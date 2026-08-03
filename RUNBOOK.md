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
mlsec-benchmark run-smoke
```

```bash
# Linux/macOS
export MLSEC_BENCH_SIGNING_KEY="local-dev-key"
mlsec-benchmark run-smoke
```

Results are written to `results/` as signed JSON.

## Validate Results

Check that a result file has a valid HMAC signature and conforms to the schema:

```bash
mlsec-benchmark validate results/smoke-result.json
```

## List Benchmark Contracts

See which products have registered benchmark contracts:

```bash
mlsec-benchmark list-contracts
```

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
