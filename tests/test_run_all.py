"""Tests for the run-all CLI command."""

import json
from pathlib import Path
from unittest.mock import patch

from mlsec_benchmark_suite.cli import main

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _make_mock_iam():
    """Return a mock result for the IAM lint adapter."""
    return {
        "results": {
            "iam_lint": {
                "contract": "iam-lint-v1",
                "fixture_count": 3,
                "aggregate_metrics": {
                    "total_tp": 12,
                    "total_fp": 0,
                    "total_fn": 0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                },
                "per_fixture": [],
            }
        }
    }


def _make_mock_hf():
    """Return a mock result for the HF scanner adapter."""
    return {
        "results": {
            "hf_scanner": {
                "contract": "hf-scanner-v1",
                "fixture_count": 5,
                "aggregate_metrics": {
                    "total_tp": 3,
                    "total_fp": 0,
                    "total_fn": 0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                },
                "per_fixture": [],
            }
        }
    }


def _make_mock_pi():
    """Return a mock result for the prompt injection adapter."""
    return {
        "results": {
            "prompt_injection": {
                "contract": "prompt-injection-v1",
                "total_samples": 20,
                "aggregate_metrics": {
                    "total_tp": 9,
                    "total_fp": 1,
                    "total_fn": 1,
                    "detection_rate": 0.9,
                    "false_positive_rate": 0.1,
                    "precision": 0.9,
                    "recall": 0.9,
                    "f1": 0.9,
                },
                "per_sample": [],
            }
        }
    }


def _make_mock_sp():
    """Return a mock result for the spectral adapter."""
    return {
        "results": {
            "spectral": {
                "contract": "spectral-v1",
                "data_config": {},
                "aggregate_metrics": {
                    "total_samples": 200,
                    "total_poisoned": 10,
                    "total_detected": 15,
                    "total_tp": 5,
                    "total_fp": 10,
                    "total_fn": 5,
                    "detection_rate": 0.5,
                    "precision": 0.333,
                    "recall": 0.5,
                    "f1": 0.4,
                },
            }
        }
    }


@patch(
    "mlsec_benchmark_suite.adapters.iam_lint_adapter.run_benchmark", return_value=_make_mock_iam()
)
@patch(
    "mlsec_benchmark_suite.adapters.hf_scanner_adapter.run_benchmark", return_value=_make_mock_hf()
)
@patch(
    "mlsec_benchmark_suite.adapters.prompt_injection_adapter.run_benchmark",
    return_value=_make_mock_pi(),
)
@patch(
    "mlsec_benchmark_suite.adapters.spectral_adapter.run_benchmark", return_value=_make_mock_sp()
)
def test_run_all_produces_combined_output(mock_sp, mock_pi, mock_hf, mock_iam, tmp_path):
    output = tmp_path / "all_results.json"
    main(
        [
            "run-all",
            "--output",
            output.as_posix(),
            "--fixtures-dir",
            FIXTURES_DIR.as_posix(),
        ]
    )

    assert output.exists()
    result = json.loads(output.read_text(encoding="utf-8"))
    assert "iam_lint" in result["results"]
    assert "hf_scanner" in result["results"]
    assert "prompt_injection" in result["results"]
    assert "spectral" in result["results"]
    assert len(result["adapters_run"]) == 4
    assert result["adapters_failed"] == []


@patch(
    "mlsec_benchmark_suite.adapters.iam_lint_adapter.run_benchmark", return_value=_make_mock_iam()
)
@patch(
    "mlsec_benchmark_suite.adapters.hf_scanner_adapter.run_benchmark",
    side_effect=ImportError("scanner not installed"),
)
@patch(
    "mlsec_benchmark_suite.adapters.prompt_injection_adapter.run_benchmark",
    return_value=_make_mock_pi(),
)
@patch(
    "mlsec_benchmark_suite.adapters.spectral_adapter.run_benchmark", return_value=_make_mock_sp()
)
def test_run_all_returns_nonzero_on_adapter_failure(mock_sp, mock_pi, mock_hf, mock_iam, tmp_path):
    output = tmp_path / "partial_results.json"
    rc = main(
        [
            "run-all",
            "--output",
            output.as_posix(),
            "--fixtures-dir",
            FIXTURES_DIR.as_posix(),
        ]
    )

    assert rc == 1
    assert output.exists()
    result = json.loads(output.read_text(encoding="utf-8"))
    # Should still have 3 successful adapters
    assert "iam_lint" in result["results"]
    assert "prompt_injection" in result["results"]
    assert "spectral" in result["results"]
    # HF scanner should be in errors
    assert len(result["adapters_failed"]) == 1
    assert "hf-scanner" in result["adapters_failed"][0]


@patch(
    "mlsec_benchmark_suite.adapters.iam_lint_adapter.run_benchmark", return_value=_make_mock_iam()
)
@patch(
    "mlsec_benchmark_suite.adapters.hf_scanner_adapter.run_benchmark",
    side_effect=ImportError("scanner not installed"),
)
@patch(
    "mlsec_benchmark_suite.adapters.prompt_injection_adapter.run_benchmark",
    return_value=_make_mock_pi(),
)
@patch(
    "mlsec_benchmark_suite.adapters.spectral_adapter.run_benchmark", return_value=_make_mock_sp()
)
def test_run_all_allow_partial_returns_zero(mock_sp, mock_pi, mock_hf, mock_iam, tmp_path):
    output = tmp_path / "partial_results.json"
    rc = main(
        [
            "run-all",
            "--output",
            output.as_posix(),
            "--fixtures-dir",
            FIXTURES_DIR.as_posix(),
            "--allow-partial",
        ]
    )

    assert rc == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert len(result["adapters_failed"]) == 1
