# Benchmark Methodology

This document defines the measurement methodology, statistical rigor, and reproducibility
requirements for the ML Security Benchmark Suite. All benchmark results produced by this
suite conform to these standards.

---

## 1. What Is Measured

The benchmark suite evaluates ML security tools across four primary dimensions:

### 1.1 Detection Rate (True Positive Rate / Recall)

Detection rate measures the fraction of known-malicious inputs that a tool correctly
identifies as threats.

```
detection_rate = true_positives / (true_positives + false_negatives)
```

- **Fixture sets**: Each adapter defines a labeled corpus of known-good and known-bad
  inputs (e.g., IAM policies, HuggingFace model configs, prompt injection attempts).
- **Ground truth**: Labels are manually curated and version-controlled in `fixtures/`.
- **Minimum fixture count**: Each category requires ≥ 20 labeled samples (≥ 10 positive,
  ≥ 10 negative) for full benchmarks. Smoke tests use reduced sets.

### 1.2 False Positive Rate (Type I Error)

False positive rate measures how often a tool incorrectly flags benign inputs as threats.

```
false_positive_rate = false_positives / (false_positives + true_negatives)
```

- Benchmarked against labeled clean inputs that must not trigger alerts.
- Critical for CI gate decisions: a tool with FPR > 5% is unsuitable for blocking gates.
- Measured independently per category and reported alongside detection rate.

### 1.3 Latency

Latency captures end-to-end wall-clock time for a tool to process a single input or batch.

- **Per-item latency**: Time from input submission to verdict, measured via
  `time.perf_counter_ns()` for sub-millisecond precision.
- **Batch throughput**: Items processed per second under batch workloads.
- **Cold-start latency**: First invocation after process start (captures model loading,
  JIT compilation, etc.).
- **Warm latency**: Subsequent invocations (steady-state performance).
- Latency is reported as p50, p95, p99, and mean with 95% confidence intervals.

### 1.4 Resource Usage

Resource consumption is tracked to assess deployment feasibility:

- **Peak memory (RSS)**: Maximum resident set size during benchmark execution.
- **CPU time**: User + system CPU seconds consumed.
- **GPU memory** (if applicable): Peak GPU VRAM allocation.
- **Disk I/O**: Total bytes read/written during execution.

Resource metrics are collected via `resource.getrusage()` on Unix and `psutil` where
available. GPU metrics use `pynvml` when NVIDIA hardware is detected.

---

## 2. Statistical Rigor

### 2.1 Confidence Intervals

All aggregate metrics are reported with 95% confidence intervals using the normal
approximation for large samples and Student's t-distribution for small samples:

```python
margin = t_critical * (stdev / sqrt(n))
ci_95 = (mean - margin, mean + margin)
```

- For n ≥ 30: z = 1.96 (normal approximation)
- For n < 30: t-value from Student's t-distribution with n-1 degrees of freedom
- Confidence intervals are computed by `mean_ci()` in the core library

### 2.2 Significance Testing

When comparing two tools or two versions of the same tool:

- **Paired t-test**: Used when both tools are evaluated on the same fixture set.
  Null hypothesis: no difference in mean performance.
- **McNemar's test**: Used for binary classification outcomes (detected/missed) to
  assess whether disagreements between tools are statistically significant.
- **Minimum significance level**: α = 0.05. Results with p > 0.05 are reported as
  "no significant difference detected."
- **Effect size**: Cohen's d is reported alongside p-values to quantify practical
  significance.

### 2.3 Multiple Comparisons Correction

When comparing more than two tools simultaneously:

- Bonferroni correction is applied: α_adjusted = 0.05 / k (where k = number of
  comparisons).
- Results tables indicate which comparisons survive correction.

### 2.4 Bootstrap Confidence Intervals

For metrics where normality assumptions may not hold (e.g., latency distributions):

- 10,000 bootstrap resamples are drawn with replacement.
- The 2.5th and 97.5th percentiles of the bootstrap distribution form the 95% CI.
- Bootstrap is the default for latency metrics; parametric CI is the default for
  rates and proportions.

### 2.5 Minimum Sample Requirements

| Metric Type        | Minimum Samples | Rationale                          |
|--------------------|----------------:|-------------------------------------|
| Detection rate     |              50 | Sufficient for ±14% CI at 95%      |
| False positive rate|             100 | Low base rate requires more samples |
| Latency            |              30 | CLT applicability threshold         |
| Resource usage     |              10 | High variance acceptable            |

Smoke tests relax these requirements (n=12 per category) and are explicitly marked
as non-authoritative in result metadata.

---

## 3. Baseline Comparisons

### 3.1 Baseline Definition

Every benchmark category defines a baseline comparator:

- **Random baseline**: A classifier that outputs labels uniformly at random.
  Expected detection rate = 0.5 for balanced datasets.
- **Majority-class baseline**: A classifier that always predicts the majority class.
  Establishes the floor for imbalanced datasets.
- **Previous version**: When benchmarking a tool update, the prior release serves
  as the comparison baseline.

### 3.2 Relative Improvement Reporting

Results are reported both in absolute terms and relative to baselines:

```
relative_improvement = (tool_metric - baseline_metric) / baseline_metric × 100%
```

A tool must exceed the random baseline with p < 0.05 to be considered functional.
A tool must exceed the majority-class baseline to demonstrate practical utility.

### 3.3 Regression Detection

CI pipelines compare current results against the most recent passing benchmark:

- If any metric degrades beyond its confidence interval, the run is flagged.
- Regression threshold: mean drops by more than 1 standard deviation from historical
  mean across the last 5 runs.
- Grace period: new categories are exempt from regression checks for 3 runs after
  introduction.

---

## 4. Reproducibility Requirements

### 4.1 Input Identity

Every benchmark result includes a cryptographic identity block (`input_identity`)
that pins all inputs:

| Field                   | Description                                      |
|-------------------------|--------------------------------------------------|
| `repository`            | Source repository (e.g., `poojakira/tool-name`)  |
| `repository_commit`     | Full SHA of the tool under test                  |
| `artifact_digest`       | SHA-256 of the built artifact (wheel/binary)     |
| `model_hash`            | SHA-256 of model weights (if applicable)         |
| `dataset_hash`          | SHA-256 of the fixture/dataset manifest          |
| `configuration_hash`    | SHA-256 of the benchmark configuration           |
| `dependency_lock_hash`  | SHA-256 of the lockfile (requirements.txt, etc.) |
| `seeds`                 | Random seeds used for stochastic operations      |

### 4.2 Deterministic Execution

- All random operations use seeded PRNGs. Seeds are recorded in result metadata.
- Benchmark order is fixed (alphabetical by category, then by seed).
- Non-deterministic tools (e.g., those using LLM APIs) must run multiple seeds
  and report variance across runs.

### 4.3 Environment Recording

Each result captures:

```json
{
  "python": "3.12.4",
  "platform": "Linux-6.5.0-x86_64",
  "machine": "x86_64",
  "processor": "x86_64"
}
```

Additional environment data for full benchmarks:
- CUDA version and GPU model (if applicable)
- Available RAM and CPU core count
- Container image digest (if running in Docker)

### 4.4 Artifact Integrity

- Results are signed with HMAC-SHA256 when `MLSEC_BENCH_SIGNING_KEY` is set.
- Unsigned results are accepted in development but rejected in release pipelines.
- The `validate` command verifies structural completeness and signature integrity.

### 4.5 Dataset Versioning

- Fixture files are version-controlled alongside the benchmark code.
- The dataset manifest (`datasets/smoke-fixtures.json`) records hashes of all
  fixture files.
- Any fixture change requires a manifest update and invalidates prior results
  for comparison purposes.

---

## 5. Hardware Normalization

### 5.1 Problem Statement

Latency and resource metrics are hardware-dependent. A result of "50ms per item"
is meaningless without hardware context. The suite addresses this through
normalization and classification.

### 5.2 Hardware Tiers

Results are tagged with a hardware tier for fair comparison:

| Tier       | Description                              | Example                    |
|------------|------------------------------------------|----------------------------|
| `ci-small` | GitHub Actions / small CI runner         | 2 vCPU, 7 GB RAM          |
| `ci-large` | Large CI runner or dedicated build host  | 8 vCPU, 32 GB RAM         |
| `dev`      | Developer workstation                    | Variable                   |
| `gpu-t4`   | Single T4 GPU instance                  | g4dn.xlarge equivalent     |
| `gpu-a10`  | Single A10G GPU instance                | g5.xlarge equivalent       |

### 5.3 Normalization Method

For cross-hardware comparison, latency metrics are normalized:

1. **Reference calibration**: A standard compute kernel (matrix multiply of fixed
   size) is run at benchmark start. The wall-clock time establishes a hardware
   speed factor.
2. **Normalized latency**: `normalized_ms = raw_ms × (reference_time / baseline_reference_time)`
   where `baseline_reference_time` is the calibration result on the reference platform
   (ci-small GitHub Actions runner).
3. **Reporting**: Both raw and normalized values are stored. Comparisons use
   normalized values; absolute values use raw.

### 5.4 Thermal Throttling Mitigation

- A 5-second warmup period precedes latency measurements.
- If consecutive measurements show >20% degradation, a cooling period is inserted
  and affected samples are discarded.
- The number of discarded samples is recorded in `failure_accounting`.

### 5.5 Resource Normalization

Memory usage is reported as both:
- Absolute (MB): for deployment planning
- Relative (% of available RAM): for feasibility assessment

CPU usage is reported as:
- Wall-clock seconds: for user experience
- CPU-seconds: for efficiency (captures parallelism)

---

## 6. Benchmark Execution Protocol

### 6.1 Smoke Benchmarks

Smoke benchmarks are fast (< 30 seconds), deterministic, and run on every commit:

1. Load fixture set (embedded in package)
2. Execute tool adapter with fixed seeds
3. Compute metrics with confidence intervals
4. Compare against contract thresholds
5. Produce signed result artifact

### 6.2 Full Benchmarks

Full benchmarks are comprehensive and run on release candidates:

1. Download full dataset from manifest URLs
2. Verify dataset integrity against recorded hashes
3. Run calibration kernel for hardware normalization
4. Execute tool adapter with multiple seeds (minimum 5)
5. Collect latency, resource, and accuracy metrics
6. Compute all statistical measures
7. Compare against baselines and prior results
8. Produce signed result artifact with full raw data

### 6.3 Regression Benchmarks

Triggered when a tool dependency updates:

1. Run full benchmark on current version
2. Load prior result for the same hardware tier
3. Compute paired differences
4. Apply significance tests
5. Flag regressions exceeding threshold

---

## 7. Result Schema and Validation

### 7.1 Required Fields

Every result artifact must contain:

- `schema_version`: Semantic version of the result schema
- `suite_version`: Version of the benchmark suite that produced the result
- `created_at`: ISO 8601 timestamp with timezone
- `run_id`: Deterministic hash of inputs (for deduplication)
- `input_identity`: Full cryptographic identity block
- `environment`: Hardware and software environment
- `contract_version`: Version of the pass/fail contract applied
- `dataset_manifest`: Hash and metadata of input data
- `results`: Per-category metric dictionaries
- `raw_artifacts`: Embedded or referenced raw measurements
- `failure_accounting`: Per-category failure counts and reasons
- `signature`: HMAC-SHA256 signature or unsigned marker

### 7.2 Validation Rules

The `validate` command enforces:

1. All required fields present
2. All identity fields non-empty strings
3. All declared categories have results
4. Signature verification (if key available)
5. Schema version compatibility

---

## 8. Limitations and Non-Goals

### 8.1 Known Limitations

- Smoke benchmarks use synthetic fixtures and do not represent real-world performance.
- Hardware normalization is approximate; cross-tier comparisons have ±15% error.
- LLM-based tools have inherent non-determinism that seeds cannot fully control.
- Resource measurements on shared CI runners have high variance.

### 8.2 Non-Goals

- This suite does not benchmark model training performance.
- This suite does not evaluate tool UX, documentation quality, or API design
  (though usability scoring in the scoring framework addresses some aspects).
- This suite does not provide security certifications or compliance attestations.

---

## 9. Versioning

This methodology document is versioned alongside the benchmark suite. Breaking
changes to measurement methodology require a major version bump of the suite and
invalidate prior results for direct comparison.

| Suite Version | Methodology Version | Change Summary                     |
|---------------|--------------------:|-------------------------------------|
| 1.0.0         |               1.0.0 | Initial methodology                 |

---

## 10. References

- Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences.
- Efron, B., & Tibshirani, R. J. (1993). An Introduction to the Bootstrap.
- Georges, A., Buytaert, D., & Eeckhout, L. (2007). Statistically Rigorous
  Java Performance Evaluation. OOPSLA '07.
- Fleming, P. J., & Wallace, J. J. (1986). How not to lie with statistics:
  the correct way to summarize benchmark results. CACM 29(3).
