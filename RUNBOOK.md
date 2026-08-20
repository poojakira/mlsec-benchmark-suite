# RUNBOOK — mlsec-benchmark-suite

## Prerequisites

- Python 3.9+
- pip
- ML security tools under test must be installed or accessible via Docker

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run All Benchmarks

```bash
pytest benchmarks/ -v --tb=short
```

Run a specific benchmark:
```bash
pytest benchmarks/test_mia_smoke.py -v
```

Run with timing report:
```bash
pytest benchmarks/ -v --durations=10
```

## Interpret Output

- **PASSED** — tool executed correctly and produced expected output format
- **FAILED** — tool crashed, returned malformed output, or exceeded timeout
- **SKIPPED** — dependency not available (check skip reason in output)

Key metrics in `results/benchmark_report.json`:
| Field | Meaning |
|-------|---------|
| `pass_rate` | Fraction of benchmarks passing |
| `avg_duration` | Mean execution time per benchmark |
| `failures` | List of failed test IDs with error summaries |

A healthy suite: pass_rate ≥ 0.95, no timeouts.

## Add New Benchmarks

1. Create `benchmarks/test_<tool_name>_smoke.py`
2. Follow existing pattern:
   ```python
   def test_tool_runs(tool_fixture):
       result = tool_fixture.run(input_data)
       assert result.exit_code == 0
       assert "error" not in result.stdout.lower()
   ```
3. Add any new fixtures to `conftest.py`
4. Run: `pytest benchmarks/test_<tool_name>_smoke.py -v`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| All tests skipped | Install required tools or set `TOOL_PATH` env vars |
| Timeout failures | Increase with `--timeout=120` or check tool performance |
| Import errors | Ensure venv is activated and deps installed |
| Flaky tests | Check for race conditions; use `--forked` for isolation |
