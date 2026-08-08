"""Tests for the prompt injection benchmark adapter."""

from unittest.mock import patch


def _mock_detect_injection(text: str):
    """Mock that detects common injection patterns."""
    injection_indicators = [
        "ignore", "previous instructions", "system prompt",
        "developer mode", "DAN", "disregard", "override",
        "im_end", "im_start", "PWNED", "HACKED",
        "new persona", "no longer an AI", "malware",
        "Execute:", "rm -rf",
    ]
    is_injection = any(indicator.lower() in text.lower() for indicator in injection_indicators)
    return {"is_injection": is_injection, "confidence": 0.95 if is_injection else 0.05}


@patch("mlsec_benchmark_suite.adapters.prompt_injection_adapter.detect_injection", _mock_detect_injection)
def test_adapter_produces_valid_result():
    from mlsec_benchmark_suite.adapters.prompt_injection_adapter import run_benchmark

    result = run_benchmark()

    assert result["schema_version"] == "1.0.0"
    assert result["suite_version"] == "0.1.0"
    assert result["run_id"]
    assert result["created_at"]
    assert result["contract_version"] == "prompt-injection-v1"
    assert result["signature"]["algorithm"] == "unsigned"
    assert result["signature"]["payload_sha256"]


@patch("mlsec_benchmark_suite.adapters.prompt_injection_adapter.detect_injection", _mock_detect_injection)
def test_adapter_detects_injections():
    from mlsec_benchmark_suite.adapters.prompt_injection_adapter import run_benchmark

    result = run_benchmark()
    metrics = result["results"]["prompt_injection"]["aggregate_metrics"]

    # Should detect most injections
    assert metrics["detection_rate"] >= 0.8
    assert metrics["total_tp"] >= 8


@patch("mlsec_benchmark_suite.adapters.prompt_injection_adapter.detect_injection", _mock_detect_injection)
def test_adapter_low_false_positive_rate():
    from mlsec_benchmark_suite.adapters.prompt_injection_adapter import run_benchmark

    result = run_benchmark()
    metrics = result["results"]["prompt_injection"]["aggregate_metrics"]

    # Should have low FP rate on benign strings
    assert metrics["false_positive_rate"] <= 0.2


@patch("mlsec_benchmark_suite.adapters.prompt_injection_adapter.detect_injection", _mock_detect_injection)
def test_adapter_reports_correct_sample_counts():
    from mlsec_benchmark_suite.adapters.prompt_injection_adapter import (
        BENIGN_SAMPLES,
        INJECTION_SAMPLES,
        run_benchmark,
    )

    result = run_benchmark()
    result_data = result["results"]["prompt_injection"]

    assert result_data["injection_samples"] == len(INJECTION_SAMPLES)
    assert result_data["benign_samples"] == len(BENIGN_SAMPLES)
    assert result_data["total_samples"] == len(INJECTION_SAMPLES) + len(BENIGN_SAMPLES)
    assert len(result_data["per_sample"]) == result_data["total_samples"]
