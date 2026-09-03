"""Tests for the HF scanner benchmark adapter."""

from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "hf_configs"

# Detect whether the REAL sibling detector is importable. The real-adapter
# integration test below runs the genuine scanner (no mock) when available and
# is skipped otherwise, so `pytest tests/` stays green with no siblings installed.
try:
    from scanner.analyzer.config_scanner import (  # noqa: F401
        analyze_config_file as _real_analyze,
    )

    _REAL_SCANNER_AVAILABLE = True
except ImportError:
    _REAL_SCANNER_AVAILABLE = False


def _mock_analyze_config_file(path: str, source: str):
    """Mock that returns findings for known-bad configs, empty for known-good.

    Mirrors the real ``analyze_config_file(file_path, source)`` contract: the
    adapter passes the fixture's raw *contents* as ``source`` (not the filename),
    so this mock keys off the file path.
    """
    assert isinstance(source, str) and source  # real adapter passes file contents
    path_str = str(path)
    if "bad_pickle_exec" in path_str:
        return [{"rule": "HF001", "severity": "critical", "message": "Pickle execution detected"}]
    elif "bad_unsigned_weights" in path_str:
        return [
            {
                "rule": "HF002",
                "severity": "high",
                "message": "Unsigned weights from untrusted source",
            }
        ]
    elif "bad_suspicious_url" in path_str:
        return [
            {"rule": "HF003", "severity": "high", "message": "Suspicious external URL in auto_map"}
        ]
    return []


@patch(
    "mlsec_benchmark_suite.adapters.hf_scanner_adapter.analyze_config_file",
    _mock_analyze_config_file,
)
def test_adapter_produces_valid_result():
    from mlsec_benchmark_suite.adapters.hf_scanner_adapter import run_benchmark

    result = run_benchmark(fixtures_dir=FIXTURES_DIR)

    assert result["schema_version"] == "1.0.0"
    assert result["suite_version"] == "0.1.0"
    assert result["run_id"]
    assert result["created_at"]
    assert result["contract_version"] == "hf-scanner-v1"
    assert result["signature"]["algorithm"] == "unsigned"
    assert result["signature"]["payload_sha256"]


@patch(
    "mlsec_benchmark_suite.adapters.hf_scanner_adapter.analyze_config_file",
    _mock_analyze_config_file,
)
def test_adapter_detects_all_bad_configs():
    from mlsec_benchmark_suite.adapters.hf_scanner_adapter import run_benchmark

    result = run_benchmark(fixtures_dir=FIXTURES_DIR)
    metrics = result["results"]["hf_scanner"]["aggregate_metrics"]

    # All bad configs should be detected (recall=1.0)
    assert metrics["recall"] == 1.0
    assert metrics["total_fn"] == 0


@patch(
    "mlsec_benchmark_suite.adapters.hf_scanner_adapter.analyze_config_file",
    _mock_analyze_config_file,
)
def test_adapter_has_no_false_positives():
    from mlsec_benchmark_suite.adapters.hf_scanner_adapter import run_benchmark

    result = run_benchmark(fixtures_dir=FIXTURES_DIR)
    metrics = result["results"]["hf_scanner"]["aggregate_metrics"]

    # No false positives on clean configs
    assert metrics["precision"] == 1.0
    assert metrics["total_fp"] == 0


@patch(
    "mlsec_benchmark_suite.adapters.hf_scanner_adapter.analyze_config_file",
    _mock_analyze_config_file,
)
def test_clean_configs_produce_zero_findings():
    from mlsec_benchmark_suite.adapters.hf_scanner_adapter import run_benchmark

    result = run_benchmark(fixtures_dir=FIXTURES_DIR)
    per_fixture = result["results"]["hf_scanner"]["per_fixture"]

    clean_fixtures = [f for f in per_fixture if f["label"] == "known-good"]
    assert len(clean_fixtures) == 2
    for fixture in clean_fixtures:
        assert fixture["metrics"]["tp"] == 0
        assert fixture["metrics"]["fp"] == 0
        assert fixture["metrics"]["fn"] == 0
        assert fixture["detected_findings"] == 0


@patch(
    "mlsec_benchmark_suite.adapters.hf_scanner_adapter.analyze_config_file",
    _mock_analyze_config_file,
)
def test_bad_configs_produce_findings():
    from mlsec_benchmark_suite.adapters.hf_scanner_adapter import run_benchmark

    result = run_benchmark(fixtures_dir=FIXTURES_DIR)
    per_fixture = result["results"]["hf_scanner"]["per_fixture"]

    bad_fixtures = [f for f in per_fixture if f["label"] == "known-bad"]
    assert len(bad_fixtures) == 3
    for fixture in bad_fixtures:
        assert fixture["metrics"]["tp"] == 1
        assert fixture["detected_findings"] > 0


# ---------------------------------------------------------------------------
# REAL adapter integration test (no mock). Runs the genuine
# hf-model-provenance-scanner detector against committed fixtures. Skipped
# automatically when the sibling package is not importable.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _REAL_SCANNER_AVAILABLE,
    reason="hf-model-provenance-scanner (scanner.analyzer.config_scanner) not installed",
)
def test_real_scanner_detects_all_bad_and_no_false_positives():
    """Invoke the REAL detector end-to-end and assert measured metrics.

    This is not a mock: it imports and calls the real
    ``scanner.analyzer.config_scanner.analyze_config_file`` against the
    committed known-good/known-bad fixtures.
    """
    from mlsec_benchmark_suite.adapters.hf_scanner_adapter import run_benchmark

    result = run_benchmark(fixtures_dir=FIXTURES_DIR)
    metrics = result["results"]["hf_scanner"]["aggregate_metrics"]

    # Measured from the real detector on 2026-09: all 3 bad fixtures flagged
    # (recall=1.0), no false positives on the 2 clean fixtures (precision=1.0).
    assert metrics["recall"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["total_fp"] == 0
    assert metrics["total_fn"] == 0
    assert metrics["total_tp"] == 3

    # Findings must be JSON-serializable dicts (real Finding dataclasses get
    # converted), each carrying a real rule id from the scanner.
    per_fixture = result["results"]["hf_scanner"]["per_fixture"]
    for fixture in per_fixture:
        if fixture["label"] == "known-bad":
            assert fixture["findings_detail"], fixture["fixture"]
            for finding in fixture["findings_detail"]:
                assert isinstance(finding, dict)
                assert finding["rule"], finding
