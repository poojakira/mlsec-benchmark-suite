# Scoring Framework

This document defines how ML security tools are scored across dimensions, how
composite scores are calculated, and what thresholds gate CI pass/fail decisions.

---

## 1. Scoring Dimensions

Each tool is evaluated across four orthogonal dimensions:

| Dimension   | Weight | Description                                          |
|-------------|-------:|------------------------------------------------------|
| Accuracy    |   0.40 | Correctness of threat detection and classification   |
| Speed       |   0.25 | Latency and throughput under benchmark workloads     |
| Coverage    |   0.20 | Breadth of threat categories and input types handled |
| Usability   |   0.15 | Integration ease, error reporting, configurability   |

---

## 2. Accuracy Scoring (Weight: 0.40)

### 2.1 Metrics

| Metric              | Description                                | Target   |
|---------------------|--------------------------------------------|----------|
| Precision           | TP / (TP + FP)                             | ≥ 0.90   |
| Recall              | TP / (TP + FN)                             | ≥ 0.85   |
| F1 Score            | Harmonic mean of precision and recall      | ≥ 0.87   |
| False Positive Rate | FP / (FP + TN)                             | ≤ 0.05   |
| AUC-ROC             | Area under ROC curve (if scores available) | ≥ 0.92   |

### 2.2 Accuracy Score Calculation

The accuracy dimension score is computed as a weighted combination:

```
accuracy_score = (
    0.30 × normalize(f1, min=0.5, max=1.0) +
    0.25 × normalize(precision, min=0.5, max=1.0) +
    0.25 × normalize(recall, min=0.5, max=1.0) +
    0.20 × normalize(1 - fpr, min=0.5, max=1.0)
)
```

Where `normalize(value, min, max) = clamp((value - min) / (max - min), 0, 1)`.

### 2.3 Category-Specific Adjustments

Some categories weight precision over recall (e.g., CI gates where false positives
block deployments), while others weight recall (e.g., security scanners where missed
threats are critical). Category-specific overrides are declared in the contract JSON.

---

## 3. Speed Scoring (Weight: 0.25)

### 3.1 Metrics

| Metric                  | Description                            | Target        |
|-------------------------|----------------------------------------|---------------|
| p50 latency             | Median per-item processing time        | ≤ 100ms       |
| p95 latency             | 95th percentile latency                | ≤ 500ms       |
| p99 latency             | 99th percentile latency                | ≤ 1000ms      |
| Throughput              | Items processed per second             | ≥ 10 items/s  |
| Cold-start overhead     | First-invocation latency penalty       | ≤ 5s          |

### 3.2 Speed Score Calculation

```
speed_score = (
    0.35 × normalize(1/p50_ms, min=1/1000, max=1/10) +
    0.25 × normalize(1/p95_ms, min=1/5000, max=1/50) +
    0.20 × normalize(throughput, min=1, max=100) +
    0.20 × normalize(1/cold_start_s, min=1/30, max=1/1)
)
```

Latency values are hardware-normalized before scoring (see METHODOLOGY.md §5).

### 3.3 Latency Budget Tiers

| Tier         | p95 Budget | Use Case                              |
|--------------|------------|---------------------------------------|
| Real-time    | ≤ 50ms    | Inline request filtering              |
| Interactive  | ≤ 500ms   | IDE plugin, PR check                  |
| Batch        | ≤ 5s      | Nightly scan, release gate            |
| Offline      | ≤ 60s     | Comprehensive audit                   |

Tools are scored relative to their declared tier. A batch tool is not penalized
for latency that would fail a real-time tool.

---

## 4. Coverage Scoring (Weight: 0.20)

### 4.1 Metrics

| Metric                  | Description                                  | Target  |
|-------------------------|----------------------------------------------|---------|
| Threat category coverage| Fraction of relevant threat types detected   | ≥ 0.80  |
| Input format support    | Number of supported input formats            | ≥ 3     |
| Attack variant coverage | Fraction of known attack variants caught     | ≥ 0.75  |
| Edge case handling      | Graceful handling of malformed/edge inputs   | ≥ 0.90  |

### 4.2 Coverage Score Calculation

```
coverage_score = (
    0.40 × normalize(threat_coverage, min=0.3, max=1.0) +
    0.25 × normalize(format_support, min=1, max=10) +
    0.20 × normalize(variant_coverage, min=0.3, max=1.0) +
    0.15 × normalize(edge_handling, min=0.5, max=1.0)
)
```

### 4.3 Coverage Assessment Method

Coverage is assessed by:

1. Defining a taxonomy of threats relevant to the tool's category.
2. Creating fixture inputs for each threat type in the taxonomy.
3. Running the tool against the full fixture set.
4. Computing the fraction of threat types where recall ≥ 0.5.

The threat taxonomy is maintained in `contracts/` and versioned with the suite.

---

## 5. Usability Scoring (Weight: 0.15)

### 5.1 Metrics

| Metric                  | Description                                  | Target  |
|-------------------------|----------------------------------------------|---------|
| Exit code correctness   | Returns 0 on success, non-zero on failure    | 1.0     |
| Error message quality   | Actionable error messages on failure         | ≥ 0.80  |
| Configuration surface   | Tunable parameters without code changes      | ≥ 5     |
| Output format           | Machine-parseable structured output (JSON)   | 1.0     |
| Documentation coverage  | Fraction of features documented              | ≥ 0.80  |

### 5.2 Usability Score Calculation

```
usability_score = (
    0.25 × exit_code_correctness +
    0.25 × error_message_quality +
    0.20 × normalize(config_params, min=0, max=15) +
    0.15 × structured_output_support +
    0.15 × documentation_coverage
)
```

### 5.3 Automated Usability Checks

The following usability aspects are verified automatically:

- Tool exits with code 0 when no threats found in clean inputs.
- Tool exits with non-zero code when threats are found (or configurable behavior).
- Output is valid JSON when `--format json` is specified (or equivalent).
- `--help` produces usage information.
- Error messages include the problematic input path/identifier.

---

## 6. Composite Score Calculation

### 6.1 Formula

The composite score combines all dimensions:

```
composite = (
    0.40 × accuracy_score +
    0.25 × speed_score +
    0.20 × coverage_score +
    0.15 × usability_score
)
```

### 6.2 Score Scale

All scores (per-dimension and composite) are on a 0.0–1.0 scale:

| Score Range | Rating      | Interpretation                            |
|-------------|-------------|-------------------------------------------|
| 0.90–1.00   | Excellent   | Production-ready, best-in-class           |
| 0.75–0.89   | Good        | Production-ready with minor gaps          |
| 0.60–0.74   | Acceptable  | Usable with known limitations             |
| 0.40–0.59   | Below par   | Significant improvements needed           |
| 0.00–0.39   | Failing     | Not suitable for production use           |

### 6.3 Weighting Rationale

The weights reflect production priorities:

- **Accuracy (0.40)**: A security tool's primary value is correctness. Missed threats
  and false alarms directly impact security posture and developer trust.
- **Speed (0.25)**: Integration into CI/CD pipelines requires acceptable latency.
  Slow tools get disabled or moved to infrequent runs, reducing security value.
- **Coverage (0.20)**: Breadth of protection matters, but a tool that does one thing
  well is preferable to one that does many things poorly.
- **Usability (0.15)**: Adoption depends on developer experience, but usability is
  secondary to functional correctness.

### 6.4 Custom Weight Profiles

Organizations can override default weights via contract configuration:

```json
{
  "scoring_weights": {
    "accuracy": 0.50,
    "speed": 0.15,
    "coverage": 0.20,
    "usability": 0.15
  }
}
```

Weights must sum to 1.0. The suite validates this constraint at runtime.

---

## 7. CI Gate Thresholds

### 7.1 Pass/Fail Decision

A benchmark run passes the CI gate if ALL of the following hold:

| Criterion                          | Threshold | Behavior on Fail |
|------------------------------------|-----------|------------------|
| Composite score                    | ≥ 0.60    | Block merge       |
| Accuracy dimension                 | ≥ 0.70    | Block merge       |
| False positive rate                | ≤ 0.10    | Block merge       |
| No regression vs. prior run        | > -0.05   | Warn (soft gate)  |
| All declared categories evaluated  | 100%      | Block merge       |

### 7.2 Gate Levels

Three gate levels are available for pipeline configuration:

| Level    | Composite | Accuracy | Speed  | Coverage | Use Case          |
|----------|-----------|----------|--------|----------|-------------------|
| Strict   | ≥ 0.80    | ≥ 0.85   | ≥ 0.70 | ≥ 0.75   | Release candidate |
| Standard | ≥ 0.60    | ≥ 0.70   | ≥ 0.50 | ≥ 0.60   | PR merge          |
| Smoke    | ≥ 0.40    | ≥ 0.50   | N/A    | N/A      | Every commit      |

### 7.3 Regression Gate

The regression gate compares the current run against the historical baseline:

```
regression_detected = (current_composite - baseline_composite) < -threshold
```

- **Hard regression** (threshold = -0.10): Blocks the pipeline.
- **Soft regression** (threshold = -0.05): Emits a warning annotation.
- Baseline is the mean composite score of the last 5 passing runs on the same
  hardware tier.

### 7.4 Grace Period for New Tools

Tools added to the benchmark suite receive a 3-run grace period:

- First 3 runs: only the Smoke gate level is enforced.
- After 3 runs: the configured gate level takes effect.
- Grace period is tracked via the result index (`build-index` command).

---

## 8. Reporting

### 8.1 Score Card Format

Each benchmark produces a score card:

```
┌─────────────────────────────────────────────────────┐
│ ML Security Benchmark Score Card                     │
├─────────────────────────────────────────────────────┤
│ Tool: aws-agent-identity-guard @ abc1234            │
│ Date: 2026-08-24T13:00:00Z                          │
│ Gate: Standard (PR merge)                           │
├─────────────┬────────┬──────────┬───────────────────┤
│ Dimension   │ Score  │ Weight   │ Weighted          │
├─────────────┼────────┼──────────┼───────────────────┤
│ Accuracy    │  0.91  │  0.40    │  0.364            │
│ Speed       │  0.85  │  0.25    │  0.213            │
│ Coverage    │  0.78  │  0.20    │  0.156            │
│ Usability   │  0.82  │  0.15    │  0.123            │
├─────────────┼────────┼──────────┼───────────────────┤
│ COMPOSITE   │  0.856 │  1.00    │  0.856            │
├─────────────┴────────┴──────────┴───────────────────┤
│ RESULT: PASS (Standard gate: ≥ 0.60)                │
└─────────────────────────────────────────────────────┘
```

### 8.2 Trend Reporting

The `build-index` command generates a historical index that enables:

- Composite score trends over time (per tool, per category).
- Regression detection across releases.
- Cross-tool comparison within the same category.

### 8.3 Machine-Readable Output

All scores are embedded in the result JSON artifact:

```json
{
  "scoring": {
    "dimensions": {
      "accuracy": 0.91,
      "speed": 0.85,
      "coverage": 0.78,
      "usability": 0.82
    },
    "weights": {
      "accuracy": 0.40,
      "speed": 0.25,
      "coverage": 0.20,
      "usability": 0.15
    },
    "composite": 0.856,
    "gate_level": "standard",
    "gate_result": "pass"
  }
}
```

---

## 9. Extending the Framework

### 9.1 Adding a New Dimension

To add a scoring dimension:

1. Define metrics and targets in this document.
2. Implement measurement in the relevant adapter.
3. Add normalization logic to the scoring engine.
4. Update weights (must sum to 1.0) with team consensus.
5. Bump the scoring framework version.

### 9.2 Adding a New Tool

To add a tool to the benchmark:

1. Create an adapter in `mlsec_benchmark_suite/adapters/`.
2. Define fixtures in `fixtures/<category>/`.
3. Add category thresholds to the contract JSON.
4. Run 3 baseline measurements to establish the historical baseline.
5. Configure the appropriate gate level.

### 9.3 Customizing Thresholds

Per-tool threshold overrides are specified in the contract:

```json
{
  "benchmarks": {
    "iam_lint": {
      "thresholds": {
        "accuracy_min": 0.85,
        "fpr_max": 0.03,
        "p95_latency_ms": 200
      },
      "gate_level": "strict"
    }
  }
}
```

---

## 10. Versioning

| Framework Version | Change Summary                                |
|-------------------|-----------------------------------------------|
| 1.0.0             | Initial scoring framework                     |

Breaking changes to scoring methodology (weight changes, threshold changes,
dimension additions) require a minor version bump. Changes that alter the
composite score interpretation require a major version bump.
