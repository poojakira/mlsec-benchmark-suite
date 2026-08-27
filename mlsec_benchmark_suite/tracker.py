"""Continuous benchmark tracking module.

Loads historical benchmark results, computes trends per metric,
detects regressions, and generates markdown trend reports.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Trend(Enum):
    """Trend direction for a metric over time."""

    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"


@dataclass
class MetricTrend:
    """Computed trend information for a single metric."""

    name: str
    trend: Trend
    values: list[float] = field(default_factory=list)
    percent_change: float = 0.0
    regression_alert: bool = False

    @property
    def latest(self) -> float | None:
        return self.values[-1] if self.values else None

    @property
    def baseline(self) -> float | None:
        return self.values[0] if self.values else None


# Metrics where higher is better (e.g., accuracy, throughput)
HIGHER_IS_BETTER = {"accuracy", "precision", "recall", "f1_score", "throughput", "auc"}

# Metrics where lower is better (e.g., latency, error_rate)
LOWER_IS_BETTER = {"latency", "error_rate", "false_positive_rate", "memory_usage"}

# Threshold for regression alerting (10%)
REGRESSION_THRESHOLD = 0.10


def load_historical_results(results_dir: str | Path) -> list[dict[str, Any]]:
    """Load all historical benchmark result files from the results directory.

    Expects JSON files with a 'metrics' dict and an optional 'timestamp' field.
    Files are sorted by filename (expected to contain timestamps or sequence numbers).

    Args:
        results_dir: Path to the results/ directory.

    Returns:
        List of result dicts sorted chronologically.
    """
    results_path = Path(results_dir)
    if not results_path.exists():
        return []

    results: list[dict[str, Any]] = []
    for filepath in sorted(results_path.glob("*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "metrics" in data:
                data["_source_file"] = str(filepath.name)
                results.append(data)
        except (json.JSONDecodeError, OSError):
            # Skip malformed or unreadable files
            continue

    return results


def compute_trend(metric_name: str, values: list[float]) -> MetricTrend:
    """Compute the trend for a single metric given its historical values.

    Args:
        metric_name: Name of the metric.
        values: Ordered list of metric values (oldest to newest).

    Returns:
        MetricTrend with direction and regression alert status.
    """
    if len(values) < 2:
        return MetricTrend(
            name=metric_name,
            trend=Trend.STABLE,
            values=values,
            percent_change=0.0,
            regression_alert=False,
        )

    baseline = values[0]
    latest = values[-1]

    if baseline == 0:
        percent_change = 0.0 if latest == 0 else float("inf")
    else:
        percent_change = (latest - baseline) / abs(baseline)

    # Determine if this metric is higher-is-better or lower-is-better
    higher_better = metric_name.lower() in HIGHER_IS_BETTER
    lower_better = metric_name.lower() in LOWER_IS_BETTER

    # Default: assume higher is better if not explicitly categorized
    if not higher_better and not lower_better:
        higher_better = True

    # Determine trend direction
    if abs(percent_change) < 0.01:
        trend = Trend.STABLE
    elif higher_better:
        trend = Trend.IMPROVING if percent_change > 0 else Trend.DEGRADING
    else:
        trend = Trend.IMPROVING if percent_change < 0 else Trend.DEGRADING

    # Check for regression (> 10% degradation)
    regression_alert = False
    if higher_better and percent_change < -REGRESSION_THRESHOLD:
        regression_alert = True
    elif lower_better and percent_change > REGRESSION_THRESHOLD:
        regression_alert = True

    return MetricTrend(
        name=metric_name,
        trend=trend,
        values=values,
        percent_change=percent_change,
        regression_alert=regression_alert,
    )


def analyze_trends(results: list[dict[str, Any]]) -> list[MetricTrend]:
    """Analyze trends across all metrics in historical results.

    Args:
        results: List of result dicts (sorted chronologically).

    Returns:
        List of MetricTrend objects for each metric found.
    """
    if not results:
        return []

    # Collect per-metric value series
    metric_series: dict[str, list[float]] = {}
    for result in results:
        metrics = result.get("metrics", {})
        for name, value in metrics.items():
            if isinstance(value, (int, float)):
                metric_series.setdefault(name, []).append(float(value))

    # Compute trends
    trends = []
    for name, values in sorted(metric_series.items()):
        trends.append(compute_trend(name, values))

    return trends


def check_regressions(trends: list[MetricTrend]) -> list[MetricTrend]:
    """Filter trends to only those with regression alerts.

    Args:
        trends: List of all computed metric trends.

    Returns:
        List of MetricTrend objects that have regression_alert=True.
    """
    return [t for t in trends if t.regression_alert]


def generate_trend_report(trends: list[MetricTrend]) -> str:
    """Generate a markdown trend report from computed trends.

    Args:
        trends: List of MetricTrend objects.

    Returns:
        Markdown-formatted trend report string.
    """
    lines: list[str] = []
    lines.append("# Benchmark Trend Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")

    if not trends:
        lines.append("No historical data available for trend analysis.")
        lines.append("")
        return "\n".join(lines)

    improving = [t for t in trends if t.trend == Trend.IMPROVING]
    degrading = [t for t in trends if t.trend == Trend.DEGRADING]
    stable = [t for t in trends if t.trend == Trend.STABLE]
    regressions = check_regressions(trends)

    lines.append(f"- **Total metrics tracked:** {len(trends)}")
    lines.append(f"- **Improving:** {len(improving)}")
    lines.append(f"- **Stable:** {len(stable)}")
    lines.append(f"- **Degrading:** {len(degrading)}")
    lines.append(f"- **Regression alerts (>10%):** {len(regressions)}")
    lines.append("")

    # Regression alerts section
    if regressions:
        lines.append("## ⚠️ Regression Alerts")
        lines.append("")
        lines.append("The following metrics have regressed by more than 10%:")
        lines.append("")
        lines.append("| Metric | Baseline | Latest | Change |")
        lines.append("|--------|----------|--------|--------|")
        for t in regressions:
            baseline = f"{t.baseline:.4f}" if t.baseline is not None else "N/A"
            latest = f"{t.latest:.4f}" if t.latest is not None else "N/A"
            change = f"{t.percent_change:+.1%}"
            lines.append(f"| {t.name} | {baseline} | {latest} | {change} |")
        lines.append("")

    # Detailed trends table
    lines.append("## Detailed Trends")
    lines.append("")
    lines.append("| Metric | Trend | Baseline | Latest | Change |")
    lines.append("|--------|-------|----------|--------|--------|")
    for t in trends:
        icon = {"improving": "📈", "degrading": "📉", "stable": "➡️"}[t.trend.value]
        baseline = f"{t.baseline:.4f}" if t.baseline is not None else "N/A"
        latest = f"{t.latest:.4f}" if t.latest is not None else "N/A"
        change = f"{t.percent_change:+.1%}" if t.values else "N/A"
        lines.append(f"| {t.name} | {icon} {t.trend.value} | {baseline} | {latest} | {change} |")
    lines.append("")

    return "\n".join(lines)


def run_tracking(results_dir: str | Path = "results", output_file: str | None = None) -> str:
    """Run the full tracking pipeline: load, analyze, report.

    Args:
        results_dir: Path to historical results directory.
        output_file: Optional path to write the report to.

    Returns:
        The generated markdown report string.

    Raises:
        SystemExit: If any regressions are detected (exit code 1).
    """
    results = load_historical_results(results_dir)
    trends = analyze_trends(results)
    report = generate_trend_report(trends)

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

    regressions = check_regressions(trends)
    if regressions:
        print(f"❌ {len(regressions)} regression(s) detected!")
        for r in regressions:
            print(f"   - {r.name}: {r.percent_change:+.1%}")
        raise SystemExit(1)

    print(f"✅ No regressions detected. {len(trends)} metrics tracked.")
    return report


if __name__ == "__main__":
    import sys

    results_dir = sys.argv[1] if len(sys.argv) > 1 else "results"
    output = sys.argv[2] if len(sys.argv) > 2 else None
    run_tracking(results_dir, output)
