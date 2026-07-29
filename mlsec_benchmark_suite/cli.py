from __future__ import annotations

import argparse
import hashlib
import hmac
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sign_payload(payload: dict[str, Any], key: str | None) -> dict[str, str]:
    unsigned = {k: v for k, v in payload.items() if k != "signature"}
    digest = hash_json(unsigned)
    if not key:
        return {"algorithm": "unsigned", "payload_sha256": digest, "value": ""}
    value = hmac.new(key.encode("utf-8"), digest.encode("ascii"), hashlib.sha256).hexdigest()
    return {"algorithm": "hmac-sha256", "payload_sha256": digest, "value": value}


def verify_signature(payload: dict[str, Any], key: str | None) -> bool:
    signature = payload.get("signature", {})
    expected = sign_payload(payload, key)
    if signature.get("payload_sha256") != expected["payload_sha256"]:
        return False
    if signature.get("algorithm") == "unsigned":
        return not key and signature.get("value") == ""
    return bool(key) and hmac.compare_digest(signature.get("value", ""), expected["value"])


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
    return {"mean": mean, "ci95_low": mean - margin, "ci95_high": mean + margin, "sample_count": len(values)}


def category_smoke(category: str, seed: int) -> dict[str, Any]:
    rng = random.Random(f"{category}:{seed}")
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
        "hf_scanner": {"detection_rate": metrics["mean_signal"], "false_positive_rate": round(1 - metrics["mean_signal"], 6), "throughput_items_per_second": 12.0},
        "mcp_gateway": {"block_rate": metrics["mean_signal"], "bypass_resistance": round(metrics["ci95_low"], 6), "latency_ms": round(10 + metrics["mean_signal"], 6)},
        "llm_detector": {"precision": metrics["mean_signal"], "recall": round(metrics["ci95_low"], 6), "attack_success_rate": round(1 - metrics["mean_signal"], 6)},
        "dataset_poisoning": {"detection_rate": metrics["mean_signal"], "false_positive_rate": round(1 - metrics["ci95_high"], 6)},
        "model_privacy": {"attack_advantage": metrics["mean_signal"], "auroc": round(0.5 + metrics["mean_signal"] / 2, 6)},
        "adversarial_robustness": {"clean_accuracy": metrics["mean_signal"], "robust_accuracy": round(metrics["ci95_low"], 6)},
        "pulsenet": {"rul_error": round(1 - metrics["mean_signal"], 6), "anomaly_f1": metrics["mean_signal"], "serving_latency_ms": round(8 + metrics["mean_signal"], 6)},
    }
    return {"category": category, "summary": metrics, "metrics": category_metrics[category], "raw": samples}


def build_smoke_result(args: argparse.Namespace) -> dict[str, Any]:
    seeds = [int(seed) for seed in args.seeds.split(",") if seed.strip()]
    config = {"mode": "smoke", "categories": CATEGORIES, "seeds": seeds, "thresholds": load_json(args.contract)}
    dataset_manifest = load_json(args.dataset_manifest)
    raw: list[dict[str, Any]] = []
    results: dict[str, Any] = {}
    failure_accounting: dict[str, Any] = {}
    for category in CATEGORIES:
        runs = [category_smoke(category, seed) for seed in seeds]
        raw.extend({"category": category, "seed": seed, "raw": run["raw"]} for seed, run in zip(seeds, runs, strict=True))
        mean_values = [run["summary"]["mean_signal"] for run in runs]
        results[category] = {
            "contract": category,
            "seeds": seeds,
            "summary": mean_ci(mean_values),
            "metrics_by_seed": [run["metrics"] for run in runs],
            "predefined_thresholds": config["thresholds"]["benchmarks"][category]["thresholds"],
        }
        failure_accounting[category] = {"failed_runs": sum(run["summary"]["failure_count"] for run in runs), "total_runs": len(runs)}
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
        "run_id": sha256_bytes(f"{args.repository}:{args.repository_commit}:{created_at}:{seeds}".encode("utf-8"))[:16],
        "contract_version": config["thresholds"]["contract_version"],
        "dataset_manifest": dataset_manifest,
        "input_identity": identity,
        "environment": environment(),
        "results": results,
        "raw_artifacts": {"embedded_raw_sample_count": len(raw), "retention_policy": "toy smoke raw data embedded; third-party data is not committed"},
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
    for field in ["repository_commit", "artifact_digest", "model_hash", "dataset_hash", "configuration_hash", "dependency_lock_hash"]:
        value = identity[field]
        if not isinstance(value, str) or not value:
            raise ValueError(f"identity field {field} is required")
    for category in CATEGORIES:
        if category not in result["results"]:
            raise ValueError(f"missing benchmark category: {category}")
    signature = result["signature"]
    if require_signature and signature.get("algorithm") == "unsigned":
        raise ValueError("signed result required")
    key = os.environ.get("MLSEC_BENCH_SIGNING_KEY")
    if signature.get("algorithm") != "unsigned" and not verify_signature(result, key):
        raise ValueError("result signature verification failed")


def render_report(result: dict[str, Any]) -> str:
    lines = ["# ML Security Benchmark Report", "", f"Run ID: `{result['run_id']}`", f"Created: {result['created_at']}", ""]
    lines.append("## Immutable Inputs")
    for key, value in sorted(result["input_identity"].items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Category Results"])
    for category in CATEGORIES:
        summary = result["results"][category]["summary"]
        failures = result["failure_accounting"][category]
        lines.append(f"- **{category}**: mean={summary['mean']:.6f}, samples={summary['sample_count']}, failed_runs={failures['failed_runs']}")
    lines.extend(["", "## Limitations", "Smoke benchmarks use deterministic toy fixtures for CI. Full benchmarks must use manifest-declared public datasets and signed result manifests."])
    return "\n".join(lines) + "\n"


def build_index(results_dir: Path) -> dict[str, Any]:
    entries = []
    for path in sorted(results_dir.glob("*.json")):
        result = load_json(path)
        validate_result(result, require_signature=False)
        entries.append({
            "run_id": result["run_id"],
            "path": path.as_posix(),
            "created_at": result["created_at"],
            "repository": result["input_identity"]["repository"],
            "repository_commit": result["input_identity"]["repository_commit"],
            "signature": result["signature"],
        })
    return {"schema_version": "1.0.0", "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "results": entries}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mlsec-benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-smoke")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--contract", type=Path, default=PACKAGE_ROOT / "contracts" / "portfolio-smoke-v1.json")
    run.add_argument("--dataset-manifest", type=Path, default=PACKAGE_ROOT / "datasets" / "smoke-fixtures.json")
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

    index = sub.add_parser("build-index")
    index.add_argument("--results-dir", type=Path, default=Path("results"))
    index.add_argument("--output", type=Path, required=True)
    index.add_argument("--overwrite", action="store_true")

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
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())


