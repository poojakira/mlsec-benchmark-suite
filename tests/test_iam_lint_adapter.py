"""Tests for the IAM lint benchmark adapter."""

import json
from pathlib import Path

from mlsec_benchmark_suite.adapters.iam_lint_adapter import (
    GROUND_TRUTH,
    run_benchmark,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "iam_policies"


def test_adapter_produces_valid_result():
    result = run_benchmark(fixtures_dir=FIXTURES_DIR)

    # Required top-level fields
    assert result["schema_version"] == "1.0.0"
    assert result["suite_version"] == "0.1.0"
    assert result["run_id"]
    assert result["created_at"]
    assert result["contract_version"] == "iam-lint-v1"
    assert result["signature"]["algorithm"] == "unsigned"
    assert result["signature"]["payload_sha256"]


def test_adapter_detects_all_expected_rules():
    result = run_benchmark(fixtures_dir=FIXTURES_DIR)
    metrics = result["results"]["iam_lint"]["aggregate_metrics"]

    # All expected rules should be detected (recall=1.0)
    assert metrics["recall"] == 1.0
    assert metrics["total_fn"] == 0


def test_adapter_has_no_false_positives_vs_ground_truth():
    result = run_benchmark(fixtures_dir=FIXTURES_DIR)
    metrics = result["results"]["iam_lint"]["aggregate_metrics"]

    # No unexpected rules fired (precision=1.0)
    assert metrics["precision"] == 1.0
    assert metrics["total_fp"] == 0


def test_clean_policy_produces_zero_findings():
    result = run_benchmark(fixtures_dir=FIXTURES_DIR)
    per_fixture = result["results"]["iam_lint"]["per_fixture"]

    clean = next(f for f in per_fixture if f["fixture"] == "clean_bedrock_invoke.json")
    assert clean["metrics"]["tp_count"] == 0
    assert clean["metrics"]["fp_count"] == 0
    assert clean["metrics"]["fn_count"] == 0
    assert clean["detected_rules"] == []


def test_bad_policies_produce_expected_finding_counts():
    result = run_benchmark(fixtures_dir=FIXTURES_DIR)
    per_fixture = result["results"]["iam_lint"]["per_fixture"]

    bedrock = next(f for f in per_fixture if f["fixture"] == "bad_bedrock_wildcard.json")
    assert bedrock["metrics"]["tp_count"] == len(GROUND_TRUTH["bad_bedrock_wildcard.json"])

    lambda_pol = next(f for f in per_fixture if f["fixture"] == "bad_lambda_passrole.json")
    assert lambda_pol["metrics"]["tp_count"] == len(GROUND_TRUTH["bad_lambda_passrole.json"])


def test_cli_run_iam_lint(tmp_path):
    """Test CLI integration for run-iam-lint command."""
    from mlsec_benchmark_suite.cli import main

    output = tmp_path / "result.json"
    main([
        "run-iam-lint",
        "--output", output.as_posix(),
        "--fixtures-dir", FIXTURES_DIR.as_posix(),
    ])

    assert output.exists()
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["results"]["iam_lint"]["aggregate_metrics"]["f1"] == 1.0
