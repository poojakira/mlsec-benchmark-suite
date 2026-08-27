# Continuous Benchmark Tracking

This document describes how the MLSec Benchmark Suite's continuous tracking system works, including architecture, configuration, and usage.

---

## Overview

The continuous tracking system monitors benchmark metrics over time, detects performance regressions, and generates trend reports. Unlike one-shot benchmark runs, it maintains historical context and alerts when metrics degrade beyond acceptable thresholds.

### Key Capabilities

- **Historical Analysis:** Loads and analyzes all past benchmark results
- **Trend Detection:** Classifies each metric as improving, degrading, or stable
- **Regression Alerting:** Flags metrics that degrade more than 10% from baseline
- **Markdown Reports:** Generates human-readable trend reports for PR reviews
- **CI Integration:** Runs automatically on every push and PR via GitHub Actions

---

## Architecture

```
results/                      # Historical benchmark results (JSON)
├── 2024-01-15T10-30-00.json
├── 2024-01-16T10-30-00.json
└── ...

mlsec_benchmark_suite/
├── tracker.py                # Core tracking module
├── runner.py                 # Benchmark execution (produces results)
└── ...

reports/
└── trend_report.md           # Generated trend report (CI artifact)
```

### Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│  Benchmark  │────▶│   Results    │────▶│    Tracker     │────▶│  Trend       │
│  Runner     │     │  Directory   │     │  (analyzer)    │     │  Report      │
└─────────────┘     └──────────────┘     └────────────────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │  Regression  │
                                         │  Alert (CI)  │
                                         └──────────────┘
```

---

## Result File Format

Each benchmark run produces a JSON file in `results/`:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.2.0",
  "environment": {
    "python_version": "3.12.1",
    "os": "ubuntu-22.04",
    "runner": "github-actions"
  },
  "metrics": {
    "accuracy": 0.923,
    "precision": 0.911,
    "recall": 0.935,
    "f1_score": 0.923,
    "latency": 45.2,
    "throughput": 1250.0,
    "memory_usage": 512.0
  },
  "signature": "hmac-sha256:abcdef..."
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `metrics` | object | Key-value pairs of metric names to numeric values |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp of the run |
| `version` | string | Version of the benchmark suite |
| `environment` | object | Runtime environment metadata |
| `signature` | string | HMAC signature for integrity verification |

---

## Metric Classification

The tracker categorizes metrics by their optimization direction:

### Higher Is Better
Metrics where an increase indicates improvement:
- `accuracy`, `precision`, `recall`, `f1_score`
- `throughput`, `auc`

### Lower Is Better
Metrics where a decrease indicates improvement:
- `latency`, `error_rate`, `false_positive_rate`
- `memory_usage`

### Unknown Metrics
Metrics not in either list default to **higher is better**. To add custom metrics, update the `HIGHER_IS_BETTER` or `LOWER_IS_BETTER` sets in `tracker.py`.

---

## Trend Computation

### Algorithm

1. **Load:** Read all JSON files from `results/` sorted by filename
2. **Extract:** For each metric, collect the ordered list of values
3. **Compute:** Calculate percent change from baseline (first value) to latest
4. **Classify:**
   - `|change| < 1%` → **Stable**
   - Change in favorable direction → **Improving**
   - Change in unfavorable direction → **Degrading**
5. **Alert:** If degradation exceeds **10%**, flag as regression

### Regression Threshold

The default threshold is **10%** (`REGRESSION_THRESHOLD = 0.10`). This means:
- For higher-is-better metrics: alert if latest is >10% below baseline
- For lower-is-better metrics: alert if latest is >10% above baseline

To customize the threshold, modify `REGRESSION_THRESHOLD` in `tracker.py` or (in a future release) pass it as a CLI argument.

---

## Usage

### Command Line

```bash
# Basic: analyze results and print report
python -m mlsec_benchmark_suite.tracker results/

# With output file
python -m mlsec_benchmark_suite.tracker results/ reports/trend_report.md

# The tracker exits with code 1 if regressions are detected
echo $?  # 0 = clean, 1 = regressions found
```

### Programmatic

```python
from mlsec_benchmark_suite.tracker import (
    load_historical_results,
    analyze_trends,
    generate_trend_report,
    check_regressions,
)

# Load and analyze
results = load_historical_results("results/")
trends = analyze_trends(results)

# Check for regressions
regressions = check_regressions(trends)
if regressions:
    for r in regressions:
        print(f"REGRESSION: {r.name} changed {r.percent_change:+.1%}")

# Generate report
report = generate_trend_report(trends)
print(report)
```

---

## CI Integration

The tracking system is integrated into the CI pipeline via the `tracker` job in `.github/workflows/ci.yml`.

### Pipeline Flow

```
push/PR
  │
  ├── test (pytest + coverage gate at 85%)
  │     └── MUST PASS
  │
  ├── lint (ruff + mypy)
  │
  └── tracker (runs after test passes)
        ├── Run benchmarks → results/
        ├── Run trend analysis
        ├── Upload report as artifact
        └── Comment on PR (if PR event)
```

### What Happens on Regression

1. The `tracker` job exits with code 1
2. The CI pipeline fails (blocking merge)
3. A sticky comment is posted on the PR with the trend report
4. The team reviews the regression table to determine next steps

### Handling Expected Regressions

If a regression is expected (e.g., trading speed for accuracy), the team can:
1. Document the tradeoff in the PR description
2. Update the baseline after team approval
3. Get tech lead sign-off to merge with the known regression

---

## Report Format

The generated markdown report includes:

### Summary Section
```markdown
## Summary

- **Total metrics tracked:** 7
- **Improving:** 3
- **Stable:** 2
- **Degrading:** 2
- **Regression alerts (>10%):** 1
```

### Regression Alerts (if any)
```markdown
## ⚠️ Regression Alerts

| Metric | Baseline | Latest | Change |
|--------|----------|--------|--------|
| accuracy | 0.9500 | 0.8200 | -13.7% |
```

### Detailed Trends Table
```markdown
## Detailed Trends

| Metric | Trend | Baseline | Latest | Change |
|--------|-------|----------|--------|--------|
| accuracy | 📉 degrading | 0.9500 | 0.8200 | -13.7% |
| latency | 📈 improving | 50.0000 | 35.0000 | -30.0% |
| precision | ➡️ stable | 0.9100 | 0.9120 | +0.2% |
```

---

## Extending the System

### Adding New Metrics

1. Ensure your benchmark runner outputs the metric in the `metrics` dict
2. Add the metric name to `HIGHER_IS_BETTER` or `LOWER_IS_BETTER` in `tracker.py`
3. The tracker will automatically pick it up from the next run

### Custom Thresholds per Metric

For future implementation. Currently all metrics share the 10% threshold. A planned enhancement would support per-metric thresholds via a config file:

```yaml
# tracking_config.yml (planned)
thresholds:
  accuracy: 0.05    # 5% threshold for accuracy
  latency: 0.20     # 20% threshold for latency
  default: 0.10     # 10% for everything else
```

### Integration with External Systems

The tracker module can be integrated with:
- **Grafana/Prometheus:** Export metrics for dashboard visualization
- **Slack/Teams:** Post alerts to channels on regression
- **JIRA/GitHub Issues:** Auto-create issues for persistent regressions

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| No trends detected | Empty results/ directory | Run benchmarks first |
| All metrics "stable" | Only one result file | Need ≥2 runs for trends |
| False regression alert | Noisy metric | Run multiple times, average results |
| Tracker import error | Package not installed | `pip install -e ".[dev]"` |

For more complex issues, see the [Incident Runbook](../INCIDENT_RUNBOOK.md).
