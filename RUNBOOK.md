# RUNBOOK  --  mlsec-benchmark-suite

## Prerequisites

- Python 3.10+
- pip
- ML security tools under test must be installed or accessible via Docker

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Run All Benchmarks

The CLI entry point is `mlsec-benchmark` (installed via `[project.scripts]`).

Run all adapter benchmarks:
```bash
mlsec-benchmark run-all --output results/combined.json
```

Run a specific adapter benchmark:
```bash
mlsec-benchmark run-iam-lint --output results/iam_lint.json
mlsec-benchmark run-hf-scanner --output results/hf_scanner.json
mlsec-benchmark run-prompt-injection --output results/prompt_injection.json
mlsec-benchmark run-spectral --output results/spectral.json
```

Run the smoke benchmark (deterministic toy fixtures):
```bash
mlsec-benchmark run-smoke --output results/smoke.json \
  --repository-commit abc123 \
  --artifact-digest sha256:deadbeef \
  --model-hash sha256:cafebabe \
  --dependency-lock-hash sha256:feedface
```

## Run Tests

```bash
pytest tests/ -v --tb=short
```

Run a specific test file:
```bash
pytest tests/test_cli.py -v
```

Run with timing report:
```bash
pytest tests/ -v --durations=10
```

## Other CLI Commands

Validate a result file:
```bash
mlsec-benchmark validate results/smoke.json
mlsec-benchmark validate results/smoke.json --require-signature
```

Generate a markdown report from a result:
```bash
mlsec-benchmark report results/smoke.json --output reports/report.md
```

Build an index of all results:
```bash
mlsec-benchmark build-index --results-dir results --output results/index.json
```

## Interpret Output

- **PASSED**  --  adapter executed correctly and produced expected output format
- **FAILED**  --  adapter crashed, returned malformed output, or dependency missing
- **SKIPPED**  --  dependency not available (check skip reason in output)

Result JSON files contain:
| Field | Meaning |
|-------|---------|
| `results` | Per-category benchmark metrics |
| `aggregate_metrics` | Precision, recall, F1 per adapter |
| `signature` | HMAC integrity signature (set `MLSEC_BENCH_SIGNING_KEY` env var) |

## Add New Benchmarks

1. Create an adapter in `mlsec_benchmark_suite/adapters/<tool_name>_adapter.py`
2. Register the subcommand in `mlsec_benchmark_suite/cli.py`
3. Add tests in `tests/test_<tool_name>_adapter.py`
4. Run: `pytest tests/test_<tool_name>_adapter.py -v`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| All adapters fail | Install required tools or check import errors |
| Timeout failures | Increase with `--timeout=120` or check tool performance |
| Import errors | Ensure venv is activated and `pip install -e ".[dev]"` succeeded |
| Signature verification fails | Set `MLSEC_BENCH_SIGNING_KEY` environment variable |
| `--output` refuses to write | File already exists; use `--overwrite` flag |
