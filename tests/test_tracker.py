"""Tests for the continuous benchmark tracking module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlsec_benchmark_suite.tracker import (
    MetricTrend,
    Trend,
    analyze_trends,
    check_regressions,
    compute_trend,
    generate_trend_report,
    load_historical_results,
    run_tracking,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def results_dir(tmp_path: Path) -> Path:
    """Create a temporary results directory with sample data."""
    results = tmp_path / "results"
    results.mkdir()
    return results


def _write_result(directory: Path, filename: str, metrics: dict) -> None:
    """Helper to write a result JSON file."""
    data = {"metrics": metrics, "timestamp": filename.replace(".json", "")}
    with open(directory / filename, "w", encoding="utf-8") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# Test: Trend computation with improving data
# ---------------------------------------------------------------------------


class TestTrendComputationImproving:
    """Test that improving metrics are correctly detected."""

    def test_higher_is_better_improving(self):
        """Accuracy going up should be detected as improving."""
        trend = compute_trend("accuracy", [0.80, 0.85, 0.90, 0.95])
        assert trend.trend == Trend.IMPROVING
        assert trend.percent_change > 0
        assert not trend.regression_alert

    def test_lower_is_better_improving(self):
        """Latency going down should be detected as improving."""
        trend = compute_trend("latency", [100.0, 90.0, 80.0, 70.0])
        assert trend.trend == Trend.IMPROVING
        assert trend.percent_change < 0
        assert not trend.regression_alert

    def test_improving_values_stored(self):
        """Values should be stored in the MetricTrend object."""
        values = [0.70, 0.75, 0.80, 0.85]
        trend = compute_trend("f1_score", values)
        assert trend.values == values
        assert trend.latest == 0.85
        assert trend.baseline == 0.70


# ---------------------------------------------------------------------------
# Test: Regression detection
# ---------------------------------------------------------------------------


class TestRegressionDetection:
    """Test that regressions exceeding 10% threshold are flagged."""

    def test_higher_is_better_regression(self):
        """Accuracy dropping >10% should trigger regression alert."""
        trend = compute_trend("accuracy", [0.90, 0.85, 0.78])
        assert trend.trend == Trend.DEGRADING
        assert trend.regression_alert is True
        # Change is (0.78 - 0.90) / 0.90 = -0.133...
        assert trend.percent_change < -0.10

    def test_lower_is_better_regression(self):
        """Latency increasing >10% should trigger regression alert."""
        trend = compute_trend("latency", [50.0, 55.0, 60.0, 70.0])
        assert trend.trend == Trend.DEGRADING
        assert trend.regression_alert is True
        # Change is (70 - 50) / 50 = 0.40
        assert trend.percent_change > 0.10

    def test_small_degradation_no_alert(self):
        """A 5% degradation should NOT trigger a regression alert."""
        trend = compute_trend("accuracy", [1.00, 0.97, 0.95])
        # Change is -5%, below 10% threshold
        assert trend.regression_alert is False

    def test_check_regressions_filters_correctly(self):
        """check_regressions should return only alerting metrics."""
        trends = [
            MetricTrend(name="accuracy", trend=Trend.DEGRADING, values=[0.9, 0.7], percent_change=-0.22, regression_alert=True),
            MetricTrend(name="precision", trend=Trend.STABLE, values=[0.9, 0.9], percent_change=0.0, regression_alert=False),
            MetricTrend(name="latency", trend=Trend.DEGRADING, values=[50, 80], percent_change=0.60, regression_alert=True),
        ]
        regressions = check_regressions(trends)
        assert len(regressions) == 2
        assert all(r.regression_alert for r in regressions)


# ---------------------------------------------------------------------------
# Test: Stable detection
# ---------------------------------------------------------------------------


class TestStableDetection:
    """Test that stable metrics are correctly identified."""

    def test_no_change_is_stable(self):
        """Identical values should be stable."""
        trend = compute_trend("accuracy", [0.90, 0.90, 0.90, 0.90])
        assert trend.trend == Trend.STABLE
        assert not trend.regression_alert

    def test_minimal_change_is_stable(self):
        """Changes under 1% should be considered stable."""
        trend = compute_trend("accuracy", [0.900, 0.901, 0.902])
        assert trend.trend == Trend.STABLE

    def test_single_value_is_stable(self):
        """A single data point cannot determine a trend; defaults to stable."""
        trend = compute_trend("accuracy", [0.85])
        assert trend.trend == Trend.STABLE
        assert trend.percent_change == 0.0


# ---------------------------------------------------------------------------
# Test: Empty history handling
# ---------------------------------------------------------------------------


class TestEmptyHistory:
    """Test graceful handling of empty or missing historical data."""

    def test_empty_values_list(self):
        """Empty values should produce a stable trend with no alert."""
        trend = compute_trend("accuracy", [])
        assert trend.trend == Trend.STABLE
        assert trend.values == []
        assert trend.latest is None
        assert trend.baseline is None
        assert not trend.regression_alert

    def test_load_nonexistent_directory(self, tmp_path: Path):
        """Loading from a nonexistent directory should return empty list."""
        results = load_historical_results(tmp_path / "does_not_exist")
        assert results == []

    def test_analyze_trends_empty_results(self):
        """Analyzing empty results should return empty trends list."""
        trends = analyze_trends([])
        assert trends == []

    def test_load_skips_malformed_files(self, results_dir: Path):
        """Malformed JSON files should be skipped without error."""
        (results_dir / "bad.json").write_text("not valid json", encoding="utf-8")
        _write_result(results_dir, "good.json", {"accuracy": 0.9})
        results = load_historical_results(results_dir)
        assert len(results) == 1

    def test_load_skips_files_without_metrics(self, results_dir: Path):
        """JSON files missing 'metrics' key should be skipped."""
        with open(results_dir / "no_metrics.json", "w") as f:
            json.dump({"other_key": "value"}, f)
        results = load_historical_results(results_dir)
        assert results == []


# ---------------------------------------------------------------------------
# Test: Report generation format
# ---------------------------------------------------------------------------


class TestReportGeneration:
    """Test the markdown trend report output format."""

    def test_report_has_header(self):
        """Report should start with the expected markdown header."""
        trends = [
            MetricTrend(name="accuracy", trend=Trend.IMPROVING, values=[0.8, 0.9], percent_change=0.125),
        ]
        report = generate_trend_report(trends)
        assert report.startswith("# Benchmark Trend Report")

    def test_report_contains_summary(self):
        """Report should contain a summary section with counts."""
        trends = [
            MetricTrend(name="accuracy", trend=Trend.IMPROVING, values=[0.8, 0.9], percent_change=0.125),
            MetricTrend(name="latency", trend=Trend.STABLE, values=[50, 50], percent_change=0.0),
        ]
        report = generate_trend_report(trends)
        assert "## Summary" in report
        assert "**Total metrics tracked:** 2" in report
        assert "**Improving:** 1" in report
        assert "**Stable:** 1" in report

    def test_report_contains_regression_section_when_alerts(self):
        """Report should include regression alert section when regressions exist."""
        trends = [
            MetricTrend(name="accuracy", trend=Trend.DEGRADING, values=[0.9, 0.7], percent_change=-0.22, regression_alert=True),
        ]
        report = generate_trend_report(trends)
        assert "## ⚠️ Regression Alerts" in report
        assert "accuracy" in report

    def test_report_no_regression_section_when_clean(self):
        """Report should NOT include regression section when all metrics are fine."""
        trends = [
            MetricTrend(name="accuracy", trend=Trend.IMPROVING, values=[0.8, 0.9], percent_change=0.125),
        ]
        report = generate_trend_report(trends)
        assert "Regression Alerts" not in report

    def test_report_empty_data(self):
        """Report with no trends should indicate no data available."""
        report = generate_trend_report([])
        assert "No historical data available" in report

    def test_report_contains_detailed_table(self):
        """Report should contain a detailed trends table with columns."""
        trends = [
            MetricTrend(name="accuracy", trend=Trend.IMPROVING, values=[0.8, 0.9], percent_change=0.125),
        ]
        report = generate_trend_report(trends)
        assert "## Detailed Trends" in report
        assert "| Metric | Trend | Baseline | Latest | Change |" in report

    def test_report_icons(self):
        """Report should use appropriate icons for trend direction."""
        trends = [
            MetricTrend(name="a", trend=Trend.IMPROVING, values=[0.8, 0.9], percent_change=0.125),
            MetricTrend(name="b", trend=Trend.DEGRADING, values=[0.9, 0.7], percent_change=-0.22),
            MetricTrend(name="c", trend=Trend.STABLE, values=[0.5, 0.5], percent_change=0.0),
        ]
        report = generate_trend_report(trends)
        assert "📈" in report
        assert "📉" in report
        assert "➡️" in report


# ---------------------------------------------------------------------------
# Integration test: full pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Integration tests for the full tracking pipeline."""

    def test_run_tracking_no_regressions(self, results_dir: Path):
        """Pipeline should succeed when no regressions are present."""
        _write_result(results_dir, "2024-01-01.json", {"accuracy": 0.85})
        _write_result(results_dir, "2024-01-02.json", {"accuracy": 0.87})
        _write_result(results_dir, "2024-01-03.json", {"accuracy": 0.90})

        report = run_tracking(results_dir)
        assert "# Benchmark Trend Report" in report
        assert "Regression Alerts" not in report

    def test_run_tracking_with_regression_exits(self, results_dir: Path):
        """Pipeline should exit with code 1 when regressions are detected."""
        _write_result(results_dir, "2024-01-01.json", {"accuracy": 0.95})
        _write_result(results_dir, "2024-01-02.json", {"accuracy": 0.80})

        with pytest.raises(SystemExit) as exc_info:
            run_tracking(results_dir)
        assert exc_info.value.code == 1

    def test_run_tracking_writes_output_file(self, results_dir: Path, tmp_path: Path):
        """Pipeline should write report to file when output_file is specified."""
        _write_result(results_dir, "2024-01-01.json", {"accuracy": 0.85})
        _write_result(results_dir, "2024-01-02.json", {"accuracy": 0.90})

        output_file = tmp_path / "report.md"
        run_tracking(results_dir, str(output_file))

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "# Benchmark Trend Report" in content
