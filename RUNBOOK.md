# Runbook — ML Security Benchmark Suite

## Prerequisites

- Python 3.10+
- pip

## Setup

```bash
git clone https://github.com/poojakira/mlsec-benchmark-suite.git
cd mlsec-benchmark-suite
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -e ".[dev]"
```

## Run the Smoke Benchmark

The smoke benchmark exercises each product's deterministic pipeline without requiring external datasets:

```powershell
# Windows
$env:MLSEC_BENCH_SIGNING_KEY = "local-dev-key"
mlsec-benchmark run-smoke `
  --output results/smoke-result.json `
  --repository-commit $(git rev-parse HEAD) `
  --artifact-digest "sha256:local-dev" `
  --model-hash "sha256:none" `
  --dependency-lock-hash "sha256:none"
```

```bash
# Linux/macOS
export MLSEC_BENCH_SIGNING_KEY="local-dev-key"
mlsec-benchmark run-smoke \
  --output results/smoke-result.json \
  --repository-commit $(git rev-parse HEAD) \
  --artifact-digest "sha256:local-dev" \
  --model-hash "sha256:none" \
  --dependency-lock-hash "sha256:none"
```

Required flags:
- `--output` — path to write the result JSON
- `--repository-commit` — git SHA of the code being benchmarked
- `--artifact-digest` — hash of the built artifact
- `--model-hash` — hash of any model weights (use "sha256:none" if not applicable)
- `--dependency-lock-hash` — hash of requirements lock file

Optional flags:
- `--contract` — path to benchmark contract (defaults to built-in portfolio-smoke-v1.json)
- `--dataset-manifest` — path to dataset fixtures (defaults to built-in smoke-fixtures.json)
- `--repository` — repo identifier (defaults to "poojakira/mlsec-benchmark-suite")
- `--seeds` — comma-separated random seeds (defaults to "7,11,19")
- `--overwrite` — allow overwriting existing result files

Results are written as signed JSON.

## Validate Results

Check that a result file has a valid HMAC signature and conforms to the schema:

```bash
mlsec-benchmark validate results/smoke-result.json
mlsec-benchmark validate results/smoke-result.json --require-signature
```

## Generate a Report

Produce a Markdown report from a result file:

```bash
mlsec-benchmark report results/smoke-result.json --output reports/smoke-report.md
```

## Build Result Index

Index all results in a directory:

```bash
mlsec-benchmark build-index --results-dir results --output results/index.json
```

## Available Commands

| Command | Purpose |
|---------|---------|
| `run-smoke` | Run smoke benchmarks, produce signed result JSON |
| `validate` | Check result schema + optional HMAC signature |
| `report` | Generate Markdown report from result JSON |
| `build-index` | Index all result files in a directory |

## Run Tests

```bash
pytest tests/ -v
```

## View the Dashboard

```bash
python -m http.server 8080 --directory dashboard
# Open http://localhost:8080
```

Or view hosted: https://poojakira.github.io/mlsec-dashboards/mlsec-benchmark-suite/

## Project Commands

| Command | What it does |
|---------|-------------|
| `pip install -e ".[dev]"` | Install with dev dependencies |
| `mlsec-benchmark run-smoke` | Run smoke benchmarks for all products |
| `mlsec-benchmark validate <file>` | Validate a result JSON against schema + HMAC |
| `mlsec-benchmark list-contracts` | Show registered benchmark contracts |
| `pytest tests/ -v` | Run tests |
| `ruff check .` | Lint |

## How Signing Works

1. Results are serialized to stable JSON (sorted keys, no extra whitespace)
2. SHA-256 hash computed over the stable JSON bytes
3. HMAC-SHA256 computed using `MLSEC_BENCH_SIGNING_KEY`
4. Signature stored in the result file's `signature` field
5. `validate` recomputes and compares

## Known Limitations

- Only smoke tests work today — no full benchmarks with real datasets
- Product adapters are not yet implemented (each product must be tested in its own repo)
- Signing is local-only (no KMS integration)
- No comparative reporting across benchmark runs
