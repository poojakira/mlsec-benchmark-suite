from __future__ import annotations

import argparse
import hashlib
import hmac as _hmac  # aliased to avoid shadowing in sign_payload
import json
import math
import os
import platform
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parent

CATEGORIES = [
    "hf_scanner",
    "mcp_gateway",
    "llm_detector",
    "dataset_poisoning",
    "model_privacy",
    "adversarial_robustness",
    "pulsenet",
]
REQUIRED_RESULT_FIELDS = {
    "schema_version",
    "suite_version",
    "created_at",
    "run_id",
    "input_identity",
    "environment",
    "contract_version",
    "dataset_manifest",
    "results",
    "raw_artifacts",
    "failure_accounting",
    "signature",
}
REQUIRED_IDENTITY_FIELDS = {
    "repository",
    "repository_commit",
    "artifact_digest",
    "model_hash",
    "dataset_hash",
    "configuration_hash",
    "dependency_lock_hash",
    "seeds",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def hash_json(data: Any) -> str:
    return sha256_bytes(stable_json(data).encode("utf-8"))


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any, *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    if path.exists() and overwrite:
        # Overwriting a signed/committed artifact destroys prior provenance.
        # Emit a strong, visible warning (issue #1: gate --overwrite).
        print(
            f"WARNING: --overwrite is replacing existing evidence artifact: {path}. "
            "Prior provenance/signature for this file is lost and cannot be recovered.",
            file=sys.stderr,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sign_payload(payload: dict[str, Any], key: str | None) -> dict[str, str]:
    unsigned = {k: v for k, v in payload.items() if k != "signature"}
    digest = hash_json(unsigned)
    if not key:
        return {"algorithm": "unsigned", "payload_sha256": digest, "value": ""}
    # Use explicit keyword args (key=, msg=, digestmod=) to prevent argument-order bugs.
    # _hmac.new() is the three-argument HMAC constructor from the stdlib hmac module.
    mac_value = _hmac.new(
        key=key.encode("utf-8"),
        msg=digest.encode("ascii"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return {"algorithm": "hmac-sha256", "payload_sha256": digest, "value": mac_value}


def verify_signature(payload: dict[str, Any], key: str | None) -> bool:
    signature = payload.get("signature", {})
    expected = sign_payload(payload, key)
    if signature.get("payload_sha256") != expected["payload_sha256"]:
        return False
    if signature.get("algorithm") == "unsigned":
        return not key and signature.get("value") == ""
    # hmac.compare_digest performs a timing-safe comparison to prevent timing attacks.
    return bool(key) and _hmac.compare_digest(signature.get("value", ""), expected["value"])


# ---------------------------------------------------------------------------
# Ed25519 public-key signing (third-party verifiable). Unlike the shared-secret
# HMAC path, an Ed25519 signature can be verified by anyone holding only the
# PUBLIC key, so results become independently auditable (issue #1).
# ---------------------------------------------------------------------------


def _load_ed25519_private_key(pem_path: Path) -> Any:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    return load_pem_private_key(pem_path.read_bytes(), password=None)


def _load_ed25519_public_key(pem_path: Path) -> Any:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    return load_pem_public_key(pem_path.read_bytes())


def sign_payload_ed25519(payload: dict[str, Any], private_key_pem: Path) -> dict[str, str]:
    """Sign the canonical payload digest with an Ed25519 private key.

    The signature value is the hex-encoded Ed25519 signature over the ASCII
    SHA-256 hex digest of the unsigned payload. The corresponding public key is
    embedded so a third party can verify with no shared secret.
    """
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    unsigned = {k: v for k, v in payload.items() if k != "signature"}
    digest = hash_json(unsigned)
    private_key = _load_ed25519_private_key(private_key_pem)
    sig = private_key.sign(digest.encode("ascii"))
    public_pem = (
        private_key.public_key()
        .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        .decode("ascii")
    )
    return {
        "algorithm": "ed25519",
        "payload_sha256": digest,
        "value": sig.hex(),
        "public_key_pem": public_pem,
    }


def verify_signature_ed25519(payload: dict[str, Any], public_key_pem: Path | None = None) -> bool:
    """Verify an Ed25519-signed result.

    If ``public_key_pem`` is None the embedded ``public_key_pem`` in the
    signature block is used. Returns True only if the digest matches the
    recomputed payload digest AND the Ed25519 signature verifies.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    signature = payload.get("signature", {})
    if signature.get("algorithm") != "ed25519":
        return False
    unsigned = {k: v for k, v in payload.items() if k != "signature"}
    digest = hash_json(unsigned)
    if signature.get("payload_sha256") != digest:
        return False
    if public_key_pem is not None:
        public_key = _load_ed25519_public_key(public_key_pem)
    else:
        embedded = signature.get("public_key_pem")
        if not embedded:
            return False
        public_key = load_pem_public_key(embedded.encode("ascii"))
    try:
        public_key.verify(bytes.fromhex(signature.get("value", "")), digest.encode("ascii"))
    except (InvalidSignature, ValueError):
        return False
    return True


def generate_ed25519_keypair(private_out: Path, public_out: Path, *, overwrite: bool = False) -> None:
    """Generate an Ed25519 keypair and write PEM files (private + public)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    for out in (private_out, public_out):
        if out.exists() and not overwrite:
            raise FileExistsError(f"refusing to overwrite existing key: {out}")
    private_key = Ed25519PrivateKey.generate()
    private_out.parent.mkdir(parents=True, exist_ok=True)
    private_out.write_bytes(
        private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    public_out.parent.mkdir(parents=True, exist_ok=True)
    public_out.write_bytes(
        private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )


def verify_dataset_checksums(manifest: dict[str, Any], fixtures_dir: Path) -> None:
    """Recompute committed fixture checksums and compare to the manifest.

    ``manifest['files']`` (when present) maps each fixture's relative path to its
    committed ``sha256:...`` digest. This proves the benchmark ran against the
    exact committed data. Raises ValueError on any mismatch or missing file.
    """
    files = manifest.get("files")
    if not files:
        raise ValueError(
            "dataset manifest has no 'files' checksum map; cannot verify integrity"
        )
    mismatches = []
    for rel_path, expected_digest in sorted(files.items()):
        target = fixtures_dir / rel_path
        if not target.exists():
            mismatches.append(f"{rel_path}: file missing")
            continue
        actual = "sha256:" + sha256_bytes(target.read_bytes())
        if actual != expected_digest:
            mismatches.append(f"{rel_path}: expected {expected_digest}, got {actual}")
    if mismatches:
        raise ValueError("dataset checksum verification failed: " + "; ".join(mismatches))


def environment() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def mean_ci(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "ci95_low": 0.0, "ci95_high": 0.0, "sample_count": 0}
    mean = statistics.fmean(values)
    if len(values) == 1:
        return {"mean": mean, "ci95_low": mean, "ci95_high": mean, "sample_count": 1}
    stdev = statistics.stdev(values)
    margin = 1.96 * stdev / math.sqrt(len(values))
    return {
        "mean": mean,
        "ci95_low": mean - margin,
        "ci95_high": mean + margin,
        "sample_count": len(values),
    }


def category_smoke(category: str, seed: int) -> dict[str, Any]:
    rng = random.Random(f"{category}:{seed}")  # nosec B311 - deterministic benchmark sampling, not security-sensitive
    samples = [rng.random() for _ in range(12)]
    failures = sum(1 for value in samples if value < 0.03)
    base = mean_ci(samples)
    metrics = {
        "sample_count": len(samples),
        "failure_count": failures,
        "mean_signal": round(base["mean"], 6),
        "ci95_low": round(base["ci95_low"], 6),
        "ci95_high": round(base["ci95_high"], 6),
    }
    category_metrics = {
        "hf_scanner": {
            "detection_rate": metrics["mean_signal"],
            "false_positive_rate": round(1 - metrics["mean_signal"], 6),
            "throughput_items_per_second": 12.0,
        },
        "mcp_gateway": {
            "block_rate": metrics["mean_signal"],
            "bypass_resistance": round(metrics["ci95_low"], 6),
            "latency_ms": round(10 + metrics["mean_signal"], 6),
        },
        "llm_detector": {
            "precision": metrics["mean_signal"],
            "recall": round(metrics["ci95_low"], 6),
            "attack_success_rate": round(1 - metrics["mean_signal"], 6),
        },
        "dataset_poisoning": {
            "detection_rate": metrics["mean_signal"],
            "false_positive_rate": round(1 - metrics["ci95_high"], 6),
        },
        "model_privacy": {
            "attack_advantage": metrics["mean_signal"],
            "auroc": round(0.5 + metrics["mean_signal"] / 2, 6),
        },
        "adversarial_robustness": {
            "clean_accuracy": metrics["mean_signal"],
            "robust_accuracy": round(metrics["ci95_low"], 6),
        },
        "pulsenet": {
            "rul_error": round(1 - metrics["mean_signal"], 6),
            "anomaly_f1": metrics["mean_signal"],
            "serving_latency_ms": round(8 + metrics["mean_signal"], 6),
        },
    }
    return {
        "category": category,
        "summary": metrics,
        "metrics": category_metrics[category],
        "raw": samples,
    }


def build_smoke_result(args: argparse.Namespace) -> dict[str, Any]:
    seeds = [int(seed) for seed in args.seeds.split(",") if seed.strip()]
    config = {
        "mode": "smoke",
        "categories": CATEGORIES,
        "seeds": seeds,
        "thresholds": load_json(args.contract),
    }
    dataset_manifest = load_json(args.dataset_manifest)
    raw: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    failure_accounting: dict[str, Any] = {}
    for category in CATEGORIES:
        runs = [category_smoke(category, seed) for seed in seeds]
        raw.extend(
            {"category": category, "seed": seed, "raw": run["raw"]}
            for seed, run in zip(seeds, runs, strict=True)
        )
        mean_values = [run["summary"]["mean_signal"] for run in runs]
        results[category] = {
            "contract": category,
            "seeds": seeds,
            "summary": mean_ci(mean_values),
            "metrics_by_seed": [run["metrics"] for run in runs],
            "predefined_thresholds": config["thresholds"]["benchmarks"][category]["thresholds"],
        }
        failure_accounting[category] = {
            "failed_runs": sum(run["summary"]["failure_count"] for run in runs),
            "total_runs": len(runs),
        }
    identity = {
        "repository": args.repository,
        "repository_commit": args.repository_commit,
        "artifact_digest": args.artifact_digest,
        "model_hash": args.model_hash,
        "dataset_hash": dataset_manifest["dataset_hash"],
        "configuration_hash": hash_json(config),
        "dependency_lock_hash": args.dependency_lock_hash,
        "seeds": seeds,
    }
    created_at = args.created_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "schema_version": "1.0.0",
        "suite_version": "0.1.0",
        "created_at": created_at,
        "run_id": sha256_bytes(
            f"{args.repository}:{args.repository_commit}:{created_at}:{seeds}".encode()
        )[:16],
        "contract_version": config["thresholds"]["contract_version"],
        "dataset_manifest": dataset_manifest,
        "input_identity": identity,
        "environment": environment(),
        "results": results,
        "raw_artifacts": {
            "embedded_raw_sample_count": len(raw),
            "retention_policy": "toy smoke raw data embedded; third-party data is not committed",
        },
        "failure_accounting": failure_accounting,
        "signature": {},
    }
    payload["signature"] = sign_payload(payload, os.environ.get("MLSEC_BENCH_SIGNING_KEY"))
    return payload


def validate_result(result: dict[str, Any], *, require_signature: bool = False) -> None:
    missing = REQUIRED_RESULT_FIELDS - set(result)
    if missing:
        raise ValueError(f"result missing fields: {sorted(missing)}")
    identity = result["input_identity"]
    missing_identity = REQUIRED_IDENTITY_FIELDS - set(identity)
    if missing_identity:
        raise ValueError(f"input_identity missing fields: {sorted(missing_identity)}")
    for field in [
        "repository_commit",
        "artifact_digest",
        "model_hash",
        "dataset_hash",
        "configuration_hash",
        "dependency_lock_hash",
    ]:
        value = identity[field]
        if not isinstance(value, str) or not value:
            raise ValueError(f"identity field {field} is required")
    for category in CATEGORIES:
        if category not in result["results"]:
            raise ValueError(f"missing benchmark category: {category}")
    signature = result["signature"]
    if require_signature and signature.get("algorithm") == "unsigned":
        raise ValueError("signed result required")
    algorithm = signature.get("algorithm")
    if algorithm == "ed25519":
        if not verify_signature_ed25519(result, None):
            raise ValueError("result signature verification failed")
    elif algorithm != "unsigned":
        key = os.environ.get("MLSEC_BENCH_SIGNING_KEY")
        if not verify_signature(result, key):
            raise ValueError("result signature verification failed")


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# ML Security Benchmark Report",
        "",
        f"Run ID: `{result['run_id']}`",
        f"Created: {result['created_at']}",
        "",
    ]
    lines.append("## Immutable Inputs")
    for key, value in sorted(result["input_identity"].items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Category Results"])
    for category in CATEGORIES:
        summary = result["results"][category]["summary"]
        failures = result["failure_accounting"][category]
        lines.append(
            f"- **{category}**: mean={summary['mean']:.6f}, samples={summary['sample_count']}, failed_runs={failures['failed_runs']}"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "Smoke benchmarks use deterministic toy fixtures for CI. Full benchmarks must use manifest-declared public datasets and signed result manifests.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_index(results_dir: Path) -> dict[str, Any]:
    entries = []
    for path in sorted(results_dir.glob("*.json")):
        result = load_json(path)
        validate_result(result, require_signature=False)
        entries.append(
            {
                "run_id": result["run_id"],
                "path": path.as_posix(),
                "created_at": result["created_at"],
                "repository": result["input_identity"]["repository"],
                "repository_commit": result["input_identity"]["repository_commit"],
                "signature": result["signature"],
            }
        )
    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "results": entries,
    }


def _dispatch(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mlsec-benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-smoke")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument(
        "--contract", type=Path, default=PACKAGE_ROOT / "contracts" / "portfolio-smoke-v1.json"
    )
    run.add_argument(
        "--dataset-manifest", type=Path, default=PACKAGE_ROOT / "datasets" / "smoke-fixtures.json"
    )
    run.add_argument("--repository", default="poojakira/mlsec-benchmark-suite")
    run.add_argument("--repository-commit", required=True)
    run.add_argument("--artifact-digest", required=True)
    run.add_argument("--model-hash", required=True)
    run.add_argument("--dependency-lock-hash", required=True)
    run.add_argument("--seeds", default="7,11,19")
    run.add_argument("--created-at")
    run.add_argument("--overwrite", action="store_true")

    validate = sub.add_parser("validate")
    validate.add_argument("result", type=Path)
    validate.add_argument("--require-signature", action="store_true")

    report = sub.add_parser("report")
    report.add_argument("result", type=Path)
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--overwrite", action="store_true")

    iam_lint = sub.add_parser(
        "run-iam-lint", help="Run real benchmark against aws-agent-identity-guard"
    )
    iam_lint.add_argument("--output", type=Path, required=True)
    iam_lint.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "fixtures" / "iam_policies",
    )
    iam_lint.add_argument("--overwrite", action="store_true")

    hf_scanner = sub.add_parser(
        "run-hf-scanner", help="Run benchmark against hf-model-provenance-scanner"
    )
    hf_scanner.add_argument("--output", type=Path, required=True)
    hf_scanner.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "fixtures" / "hf_configs",
    )
    hf_scanner.add_argument("--overwrite", action="store_true")

    prompt_inj = sub.add_parser(
        "run-prompt-injection", help="Run benchmark against prompt injection detector"
    )
    prompt_inj.add_argument("--output", type=Path, required=True)
    prompt_inj.add_argument("--overwrite", action="store_true")

    spectral = sub.add_parser(
        "run-spectral", help="Run benchmark against spectral poisoning detector"
    )
    spectral.add_argument("--output", type=Path, required=True)
    spectral.add_argument("--overwrite", action="store_true")

    run_all = sub.add_parser(
        "run-all", help="Run all adapter benchmarks and output combined results"
    )
    run_all.add_argument("--output", type=Path, required=True)
    run_all.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "fixtures",
    )
    run_all.add_argument("--overwrite", action="store_true")
    run_all.add_argument(
        "--allow-partial",
        action="store_true",
        help="Return success even when one or more adapters fail.",
    )

    index = sub.add_parser("build-index")
    index.add_argument("--results-dir", type=Path, default=Path("results"))
    index.add_argument("--output", type=Path, required=True)
    index.add_argument("--overwrite", action="store_true")

    keygen = sub.add_parser(
        "keygen-ed25519", help="Generate an Ed25519 keypair for public-key result signing"
    )
    keygen.add_argument("--private-out", type=Path, required=True)
    keygen.add_argument("--public-out", type=Path, required=True)
    keygen.add_argument("--overwrite", action="store_true")

    sign = sub.add_parser(
        "sign", help="Re-sign an existing result with an Ed25519 private key (third-party verifiable)"
    )
    sign.add_argument("result", type=Path)
    sign.add_argument("--private-key", type=Path, required=True)
    sign.add_argument("--output", type=Path, required=True)
    sign.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser(
        "verify", help="Verify a result's signature (Ed25519 public-key or HMAC)"
    )
    verify.add_argument("result", type=Path)
    verify.add_argument(
        "--public-key",
        type=Path,
        help="Ed25519 public key PEM. If omitted, uses the public key embedded in the result.",
    )

    verify_ds = sub.add_parser(
        "verify-dataset",
        help="Recompute committed fixture checksums and compare to the dataset manifest",
    )
    verify_ds.add_argument("--manifest", type=Path, required=True)
    verify_ds.add_argument("--fixtures-dir", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "run-smoke":
        result = build_smoke_result(args)
        validate_result(result, require_signature=False)
        write_json(args.output, result, overwrite=args.overwrite)
        return 0
    if args.command == "validate":
        validate_result(load_json(args.result), require_signature=args.require_signature)
        print(f"validated {args.result}")
        return 0
    if args.command == "report":
        result = load_json(args.result)
        validate_result(result, require_signature=False)
        if args.output.exists() and not args.overwrite:
            raise FileExistsError(f"refusing to overwrite existing artifact: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_report(result), encoding="utf-8")
        return 0
    if args.command == "build-index":
        write_json(args.output, build_index(args.results_dir), overwrite=args.overwrite)
        return 0
    if args.command == "keygen-ed25519":
        generate_ed25519_keypair(args.private_out, args.public_out, overwrite=args.overwrite)
        print(f"wrote private key {args.private_out} and public key {args.public_out}")
        return 0
    if args.command == "sign":
        result = load_json(args.result)
        result["signature"] = sign_payload_ed25519(result, args.private_key)
        write_json(args.output, result, overwrite=args.overwrite)
        print(f"signed {args.result} with Ed25519 -> {args.output}")
        return 0
    if args.command == "verify":
        result = load_json(args.result)
        algorithm = result.get("signature", {}).get("algorithm")
        if algorithm == "ed25519":
            ok = verify_signature_ed25519(result, args.public_key)
        elif algorithm == "unsigned":
            print("error: result is unsigned; nothing to verify", file=sys.stderr)
            return 2
        else:
            ok = verify_signature(result, os.environ.get("MLSEC_BENCH_SIGNING_KEY"))
        if not ok:
            print("error: signature verification FAILED", file=sys.stderr)
            return 2
        print(f"signature OK ({algorithm}) for {args.result}")
        return 0
    if args.command == "verify-dataset":
        manifest = load_json(args.manifest)
        verify_dataset_checksums(manifest, args.fixtures_dir)
        print(f"dataset checksums OK: {args.fixtures_dir} matches {args.manifest}")
        return 0
    if args.command == "run-iam-lint":
        from mlsec_benchmark_suite.adapters.iam_lint_adapter import run_benchmark

        result = run_benchmark(fixtures_dir=args.fixtures_dir)
        write_json(args.output, result, overwrite=args.overwrite)
        print(
            f"IAM lint benchmark complete: "
            f"precision={result['results']['iam_lint']['aggregate_metrics']['precision']}, "
            f"recall={result['results']['iam_lint']['aggregate_metrics']['recall']}, "
            f"f1={result['results']['iam_lint']['aggregate_metrics']['f1']}"
        )
        return 0
    if args.command == "run-hf-scanner":
        from mlsec_benchmark_suite.adapters.hf_scanner_adapter import run_benchmark as run_hf

        result = run_hf(fixtures_dir=args.fixtures_dir)
        write_json(args.output, result, overwrite=args.overwrite)
        metrics = result["results"]["hf_scanner"]["aggregate_metrics"]
        print(
            f"HF scanner benchmark complete: "
            f"precision={metrics['precision']}, "
            f"recall={metrics['recall']}, "
            f"f1={metrics['f1']}"
        )
        return 0
    if args.command == "run-prompt-injection":
        from mlsec_benchmark_suite.adapters.prompt_injection_adapter import run_benchmark as run_pi

        result = run_pi()
        write_json(args.output, result, overwrite=args.overwrite)
        metrics = result["results"]["prompt_injection"]["aggregate_metrics"]
        print(
            f"Prompt injection benchmark complete: "
            f"detection_rate={metrics['detection_rate']}, "
            f"false_positive_rate={metrics['false_positive_rate']}, "
            f"f1={metrics['f1']}"
        )
        return 0
    if args.command == "run-spectral":
        from mlsec_benchmark_suite.adapters.spectral_adapter import run_benchmark as run_sp

        result = run_sp()
        write_json(args.output, result, overwrite=args.overwrite)
        metrics = result["results"]["spectral"]["aggregate_metrics"]
        print(
            f"Spectral detection benchmark complete: "
            f"detection_rate={metrics['detection_rate']}, "
            f"precision={metrics['precision']}, "
            f"f1={metrics['f1']}"
        )
        return 0
    if args.command == "run-all":
        combined_results: dict[str, Any] = {}
        errors: list[str] = []

        # IAM lint
        try:
            from mlsec_benchmark_suite.adapters.iam_lint_adapter import run_benchmark as run_iam

            iam_fixtures = args.fixtures_dir / "iam_policies"
            iam_result = run_iam(fixtures_dir=iam_fixtures)
            combined_results["iam_lint"] = iam_result["results"]["iam_lint"]
            print(f"  iam-lint: f1={iam_result['results']['iam_lint']['aggregate_metrics']['f1']}")
        except Exception as e:
            errors.append(f"iam-lint: {e}")
            print(f"  iam-lint: FAILED ({e})")

        # HF scanner
        try:
            from mlsec_benchmark_suite.adapters.hf_scanner_adapter import (
                run_benchmark as run_hf_all,
            )

            hf_fixtures = args.fixtures_dir / "hf_configs"
            hf_result = run_hf_all(fixtures_dir=hf_fixtures)
            combined_results["hf_scanner"] = hf_result["results"]["hf_scanner"]
            print(
                f"  hf-scanner: f1={hf_result['results']['hf_scanner']['aggregate_metrics']['f1']}"
            )
        except Exception as e:
            errors.append(f"hf-scanner: {e}")
            print(f"  hf-scanner: FAILED ({e})")

        # Prompt injection
        try:
            from mlsec_benchmark_suite.adapters.prompt_injection_adapter import (
                run_benchmark as run_pi_all,
            )

            pi_result = run_pi_all()
            combined_results["prompt_injection"] = pi_result["results"]["prompt_injection"]
            print(
                f"  prompt-injection: f1={pi_result['results']['prompt_injection']['aggregate_metrics']['f1']}"
            )
        except Exception as e:
            errors.append(f"prompt-injection: {e}")
            print(f"  prompt-injection: FAILED ({e})")

        # Spectral
        try:
            from mlsec_benchmark_suite.adapters.spectral_adapter import run_benchmark as run_sp_all

            sp_result = run_sp_all()
            combined_results["spectral"] = sp_result["results"]["spectral"]
            print(f"  spectral: f1={sp_result['results']['spectral']['aggregate_metrics']['f1']}")
        except Exception as e:
            errors.append(f"spectral: {e}")
            print(f"  spectral: FAILED ({e})")

        # Build combined output
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        run_id = sha256_bytes(f"run-all:{created_at}".encode())[:16]

        combined_payload: dict[str, Any] = {
            "schema_version": "1.0.0",
            "suite_version": "0.1.0",
            "created_at": created_at,
            "run_id": run_id,
            "command": "run-all",
            "adapters_run": list(combined_results.keys()),
            "adapters_failed": errors,
            "environment": environment(),
            "results": combined_results,
        }

        write_json(args.output, combined_payload, overwrite=args.overwrite)
        print(
            f"\nrun-all complete: {len(combined_results)} adapters succeeded, {len(errors)} failed"
        )
        print(f"Results written to {args.output}")
        return 0 if not errors or args.allow_partial else 1
    raise AssertionError(args.command)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint with clean error handling (no raw tracebacks on
    expected failures).

    Exit codes:
      0 - success
      2 - expected input/validation error (bad schema, existing output file,
          missing file/key)
      3 - a required sibling tool/dependency is not installed or importable
          (e.g. running ``run-hf-scanner`` without ``hf-model-provenance-scanner``)

    Note: ``validate``, ``report`` and ``build-index`` operate on ``run-smoke``
    (and per-adapter) outputs, which carry the full provenance schema. Raw
    ``run-all`` output is aggregate metrics only and is NOT a valid input to
    those commands.
    """
    try:
        return _dispatch(argv)
    except (ImportError, RuntimeError) as exc:
        # A required sibling tool is not installed/importable. This is an
        # expected, actionable condition (not a suite bug): report it cleanly
        # with a dedicated exit code instead of a raw traceback.
        print(f"error: dependency unavailable: {exc}", file=sys.stderr)
        return 3
    except (ValueError, FileExistsError, KeyError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
