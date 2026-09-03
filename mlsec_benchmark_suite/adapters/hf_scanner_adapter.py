"""Adapter connecting hf-model-provenance-scanner to mlsec-benchmark-suite.

Runs the HuggingFace model config scanner against known-good and known-bad
model configuration fixtures, computes true positives, false negatives,
false positives, and outputs results in the suite's JSON schema.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scanner.analyzer.config_scanner import analyze_config_file
except ImportError:
    analyze_config_file = None  # type: ignore[assignment]

# adapters/ -> mlsec_benchmark_suite/ -> repo root -> fixtures/hf_configs
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "hf_configs"

# Ground truth: each fixture maps to expected finding count.
# 0 means the config is clean (known-good), >0 means known-bad with that many issues.
GROUND_TRUTH: dict[str, dict[str, Any]] = {
    "clean_bert_config.json": {"expected_findings": 0, "label": "known-good"},
    "clean_gpt2_config.json": {"expected_findings": 0, "label": "known-good"},
    "bad_pickle_exec.json": {"expected_findings": 1, "label": "known-bad"},
    "bad_unsigned_weights.json": {"expected_findings": 1, "label": "known-bad"},
    "bad_suspicious_url.json": {"expected_findings": 1, "label": "known-bad"},
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding_to_dict(finding: Any) -> dict[str, Any]:
    """Serialize a scanner Finding (dataclass or dict) to a JSON-safe dict.

    The real ``scanner.models.Finding`` is a dataclass whose ``severity`` is a
    ``Severity`` enum. Mocked findings in the unit tests are already dicts.
    """
    if isinstance(finding, dict):
        return finding
    severity = getattr(finding, "severity", None)
    severity_value = getattr(severity, "value", severity)
    return {
        "rule": getattr(finding, "rule_id", None),
        "severity": severity_value,
        "message": getattr(finding, "message", None),
        "evidence": getattr(finding, "evidence", None),
        "line": getattr(finding, "line_number", None),
        "cwe": getattr(finding, "cwe", None),
    }


def _evaluate_fixture(
    fixture_name: str, fixture_path: Path, expected: dict[str, Any]
) -> dict[str, Any]:
    """Run the REAL scanner against a fixture and compute TP/FP/FN.

    The scanner's ``analyze_config_file(file_path, source)`` expects ``source``
    to be the *raw file contents* (it parses the text as JSON and pattern-matches
    against it), not the file name. We read the fixture bytes and pass the decoded
    text so the detector runs on real data.
    """
    source_text = fixture_path.read_text(encoding="utf-8")
    findings = analyze_config_file(str(fixture_path), source=source_text)
    findings = list(findings) if findings else []
    detected_count = len(findings)
    is_bad = expected["expected_findings"] > 0

    # Classification logic
    if is_bad and detected_count > 0:
        tp = 1
        fp = 0
        fn = 0
    elif is_bad and detected_count == 0:
        tp = 0
        fp = 0
        fn = 1
    elif not is_bad and detected_count == 0:
        tp = 0
        fp = 0
        fn = 0
    else:  # not is_bad and detected_count > 0
        tp = 0
        fp = 1
        fn = 0

    return {
        "fixture": fixture_name,
        "label": expected["label"],
        "expected_findings": expected["expected_findings"],
        "detected_findings": detected_count,
        "metrics": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
        },
        "findings_detail": [_finding_to_dict(f) for f in findings],
    }


def run_benchmark(fixtures_dir: Path | None = None) -> dict[str, Any]:
    """Execute the HF scanner benchmark against all fixtures.

    Returns a result dict conforming to the suite's JSON schema.
    """
    if analyze_config_file is None:
        raise ImportError(
            "hf-model-provenance-scanner is not installed. "
            "Install with: pip install hf-model-provenance-scanner"
        )
    fixtures_dir = fixtures_dir or FIXTURES_DIR
    fixture_results = []
    all_tp = 0
    all_fp = 0
    all_fn = 0

    for fixture_name, expected in sorted(GROUND_TRUTH.items()):
        fixture_path = fixtures_dir / fixture_name
        if not fixture_path.exists():
            raise FileNotFoundError(f"Missing fixture: {fixture_path}")
        result = _evaluate_fixture(fixture_name, fixture_path, expected)
        fixture_results.append(result)
        all_tp += result["metrics"]["tp"]
        all_fp += result["metrics"]["fp"]
        all_fn += result["metrics"]["fn"]

    # Aggregate metrics
    agg_precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 1.0
    agg_recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 1.0
    agg_f1 = (
        2 * agg_precision * agg_recall / (agg_precision + agg_recall)
        if (agg_precision + agg_recall) > 0
        else 0.0
    )

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    run_id = hashlib.sha256(f"hf-scanner-adapter:{created_at}".encode()).hexdigest()[:16]

    # Dataset hash from fixture contents
    fixture_hashes = []
    for name in sorted(GROUND_TRUTH.keys()):
        fixture_hashes.append(_sha256_file(fixtures_dir / name))
    dataset_hash = hashlib.sha256(":".join(fixture_hashes).encode()).hexdigest()

    config_hash = hashlib.sha256(
        json.dumps(
            {"ground_truth": {k: v for k, v in sorted(GROUND_TRUTH.items())}},
            sort_keys=True,
        ).encode()
    ).hexdigest()

    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "suite_version": "0.1.0",
        "created_at": created_at,
        "run_id": run_id,
        "contract_version": "hf-scanner-v1",
        "dataset_manifest": {
            "schema_version": "1.0.0",
            "name": "hf-scanner-fixtures",
            "source": "Hand-crafted HuggingFace model configs with known-good and known-bad patterns",
            "license": "Apache-2.0",
            "version": "0.1.0",
            "dataset_hash": f"sha256:{dataset_hash}",
            "acquisition": "Manually authored test configs for hf-model-provenance-scanner",
            "split_policy": "All fixtures used for evaluation; no train/test split needed.",
        },
        "input_identity": {
            "repository": "poojakira/hf-model-provenance-scanner",
            "repository_commit": "evaluated-locally",
            "artifact_digest": f"sha256:{dataset_hash}",
            "model_hash": "n/a-static-rules",
            "dataset_hash": f"sha256:{dataset_hash}",
            "configuration_hash": f"sha256:{config_hash}",
            "dependency_lock_hash": "evaluated-locally",
            "seeds": [],
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "adapter": "hf_scanner_adapter",
            "scanner_package": "hf-model-provenance-scanner",
        },
        "results": {
            "hf_scanner": {
                "contract": "hf-scanner-v1",
                "fixture_count": len(GROUND_TRUTH),
                "aggregate_metrics": {
                    "total_tp": all_tp,
                    "total_fp": all_fp,
                    "total_fn": all_fn,
                    "precision": round(agg_precision, 4),
                    "recall": round(agg_recall, 4),
                    "f1": round(agg_f1, 4),
                },
                "per_fixture": fixture_results,
            }
        },
        "raw_artifacts": {
            "embedded_raw_sample_count": len(fixture_results),
            "retention_policy": "All findings embedded; fixtures committed to repo.",
        },
        "failure_accounting": {
            "hf_scanner": {
                "failed_runs": all_fn,
                "total_expected": all_tp + all_fn,
                "false_positives": all_fp,
            }
        },
        "signature": {"algorithm": "unsigned", "payload_sha256": "", "value": ""},
    }

    # Compute payload hash for signature
    unsigned = {k: v for k, v in payload.items() if k != "signature"}
    payload_hash = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    payload["signature"] = {
        "algorithm": "unsigned",
        "payload_sha256": payload_hash,
        "value": "",
    }

    return payload
