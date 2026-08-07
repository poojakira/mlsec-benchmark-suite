"""Adapter connecting aws-agent-identity-guard to mlsec-benchmark-suite.

Runs the IAM policy linter against known-good and known-bad policy fixtures,
computes true positives, false negatives, false positives, and outputs results
in the suite's JSON schema.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aws_agent_identity_guard as ag

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "fixtures" / "iam_policies"

# Ground truth: each fixture maps to expected rule_ids that should fire.
# Empty set means the policy is clean (no findings expected).
GROUND_TRUTH: dict[str, set[str]] = {
    "clean_bedrock_invoke.json": set(),
    "bad_bedrock_wildcard.json": {"AIG003", "AIG006", "AIG008", "AIG013", "AIG015"},
    "bad_lambda_passrole.json": {"AIG003", "AIG004", "AIG005", "AIG006", "AIG010", "AIG013", "AIG016"},
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_policy(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _evaluate_fixture(
    fixture_name: str, policy: dict[str, Any], expected_rules: set[str]
) -> dict[str, Any]:
    """Run scanner and compute TP/FP/FN against ground truth."""
    findings = ag.scan_policy_document(policy)
    detected_rules = {f.rule_id for f in findings}

    true_positives = sorted(expected_rules & detected_rules)
    false_negatives = sorted(expected_rules - detected_rules)
    false_positives = sorted(detected_rules - expected_rules)

    tp_count = len(true_positives)
    fn_count = len(false_negatives)
    fp_count = len(false_positives)

    precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 1.0
    recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "fixture": fixture_name,
        "expected_rules": sorted(expected_rules),
        "detected_rules": sorted(detected_rules),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "metrics": {
            "tp_count": tp_count,
            "fp_count": fp_count,
            "fn_count": fn_count,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "findings_detail": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "message": f.message,
                "statement_index": f.statement_index,
            }
            for f in findings
        ],
    }


def run_benchmark(fixtures_dir: Path | None = None) -> dict[str, Any]:
    """Execute the IAM lint benchmark against all fixtures.

    Returns a result dict conforming to the suite's JSON schema.
    """
    fixtures_dir = fixtures_dir or FIXTURES_DIR
    fixture_results = []
    all_tp = 0
    all_fp = 0
    all_fn = 0

    for fixture_name, expected_rules in sorted(GROUND_TRUTH.items()):
        fixture_path = fixtures_dir / fixture_name
        if not fixture_path.exists():
            raise FileNotFoundError(f"Missing fixture: {fixture_path}")
        policy = _load_policy(fixture_path)
        result = _evaluate_fixture(fixture_name, policy, expected_rules)
        fixture_results.append(result)
        all_tp += result["metrics"]["tp_count"]
        all_fp += result["metrics"]["fp_count"]
        all_fn += result["metrics"]["fn_count"]

    # Aggregate metrics
    agg_precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 1.0
    agg_recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 1.0
    agg_f1 = (
        2 * agg_precision * agg_recall / (agg_precision + agg_recall)
        if (agg_precision + agg_recall) > 0
        else 0.0
    )

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    run_id = hashlib.sha256(
        f"iam-lint-adapter:{created_at}".encode()
    ).hexdigest()[:16]

    # Dataset hash from fixture contents
    fixture_hashes = []
    for name in sorted(GROUND_TRUTH.keys()):
        fixture_hashes.append(_sha256_file(fixtures_dir / name))
    dataset_hash = hashlib.sha256(":".join(fixture_hashes).encode()).hexdigest()

    config_hash = hashlib.sha256(
        json.dumps(
            {"ground_truth": {k: sorted(v) for k, v in GROUND_TRUTH.items()}},
            sort_keys=True,
        ).encode()
    ).hexdigest()

    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "suite_version": "0.1.0",
        "created_at": created_at,
        "run_id": run_id,
        "contract_version": "iam-lint-v1",
        "dataset_manifest": {
            "schema_version": "1.0.0",
            "name": "iam-lint-fixtures",
            "source": "Hand-crafted IAM policies with known-good and known-bad patterns",
            "license": "Apache-2.0",
            "version": "0.1.0",
            "dataset_hash": f"sha256:{dataset_hash}",
            "acquisition": "Manually authored test policies for aws-agent-identity-guard",
            "split_policy": "All fixtures used for evaluation; no train/test split needed.",
        },
        "input_identity": {
            "repository": "poojakira/aws-agent-identity-guard",
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
            "adapter": "iam_lint_adapter",
            "scanner_package": "aws-agent-identity-guard",
        },
        "results": {
            "iam_lint": {
                "contract": "iam-lint-v1",
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
            "iam_lint": {
                "failed_runs": all_fn,
                "total_rules_expected": all_tp + all_fn,
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
