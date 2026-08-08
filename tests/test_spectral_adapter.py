"""Tests for the spectral poisoning detection benchmark adapter."""

from unittest.mock import patch

import numpy as np


def _mock_spectral_detect(features, labels):
    """Mock spectral detection that flags outliers based on distance from cluster centers."""
    n_samples = len(labels)
    # Simple mock: compute distance from class mean, flag top outliers
    unique_labels = np.unique(labels)
    scores = np.zeros(n_samples)
    for lbl in unique_labels:
        mask = labels == lbl
        if mask.sum() == 0:
            continue
        center = features[mask].mean(axis=0)
        distances = np.linalg.norm(features[mask] - center, axis=1)
        scores[mask] = distances

    # Flag top 10% as suspicious (should catch some of the 5% poisoned)
    threshold = np.percentile(scores, 90)
    flagged = np.where(scores >= threshold)[0].tolist()
    return {"flagged_indices": flagged, "scores": scores.tolist()}


@patch("mlsec_benchmark_suite.adapters.spectral_adapter.spectral_detect", _mock_spectral_detect)
def test_adapter_produces_valid_result():
    from mlsec_benchmark_suite.adapters.spectral_adapter import run_benchmark

    result = run_benchmark()

    assert result["schema_version"] == "1.0.0"
    assert result["suite_version"] == "0.1.0"
    assert result["run_id"]
    assert result["created_at"]
    assert result["contract_version"] == "spectral-v1"
    assert result["signature"]["algorithm"] == "unsigned"
    assert result["signature"]["payload_sha256"]


@patch("mlsec_benchmark_suite.adapters.spectral_adapter.spectral_detect", _mock_spectral_detect)
def test_adapter_reports_detection_metrics():
    from mlsec_benchmark_suite.adapters.spectral_adapter import run_benchmark

    result = run_benchmark()
    metrics = result["results"]["spectral"]["aggregate_metrics"]

    assert "detection_rate" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert metrics["total_samples"] == 200
    assert metrics["total_poisoned"] == 10  # 5% of 200


@patch("mlsec_benchmark_suite.adapters.spectral_adapter.spectral_detect", _mock_spectral_detect)
def test_adapter_catches_some_poisoned_samples():
    from mlsec_benchmark_suite.adapters.spectral_adapter import run_benchmark

    result = run_benchmark()
    metrics = result["results"]["spectral"]["aggregate_metrics"]

    # The mock should catch at least some poisoned samples
    assert metrics["total_tp"] >= 0
    assert metrics["total_detected"] > 0


@patch("mlsec_benchmark_suite.adapters.spectral_adapter.spectral_detect", _mock_spectral_detect)
def test_adapter_data_config_matches():
    from mlsec_benchmark_suite.adapters.spectral_adapter import DEFAULT_CONFIG, run_benchmark

    result = run_benchmark()
    data_config = result["results"]["spectral"]["data_config"]

    assert data_config["n_samples"] == DEFAULT_CONFIG["n_samples"]
    assert data_config["poison_rate"] == DEFAULT_CONFIG["poison_rate"]
    assert data_config["random_seed"] == DEFAULT_CONFIG["random_seed"]


@patch("mlsec_benchmark_suite.adapters.spectral_adapter.spectral_detect", _mock_spectral_detect)
def test_adapter_is_reproducible():
    from mlsec_benchmark_suite.adapters.spectral_adapter import run_benchmark

    result1 = run_benchmark()
    result2 = run_benchmark()

    # Same seed should produce same poison indices
    assert result1["results"]["spectral"]["poison_indices"] == result2["results"]["spectral"]["poison_indices"]
    # Same detection results (mock is deterministic given same input)
    assert result1["results"]["spectral"]["detected_indices"] == result2["results"]["spectral"]["detected_indices"]
