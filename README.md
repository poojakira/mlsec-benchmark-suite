# mlsec-benchmark-suite

[![Live Dashboard](https://img.shields.io/badge/Live_Dashboard-View-blue)](https://poojakira.github.io/mlsec-benchmark-suite/)

A benchmark runner that validates ML security product claims with immutable, signed evidence.

It runs tests against ML security tools (HF model scanner, MCP gateway, LLM detector, dataset-poisoning detector, model-privacy attacks, adversarial robustness, PulseNet), records every result as a JSON artifact with cryptographic identifiers, and refuses to let you overwrite or cherry-pick results.

## What works today

**Smoke tests only.** The CLI can run a deterministic smoke benchmark that exercises the pipeline end-to-end: run tests, validate results against a JSON schema, sign results with HMAC-SHA256, and generate a Markdown report. Smoke tests prove the tooling works — they are not product performance claims.

Full benchmark datasets and product-specific adapters are not yet implemented.

## What's planned

- Public benchmark datasets for each product area
- Product-specific adapters that connect real detectors to the benchmark contracts
- Calibration and final-test dataset splits
- Comparative reporting (without comparisons to commercial products unless independently reproducible)

## Install

Requires Python 3.10+. No runtime dependencies beyond the standard library.

```
git clone https://github.com/poojakira/mlsec-benchmark-suite
cd mlsec-benchmark-suite
pip install -e .
```

Or install dev tools (pytest, ruff, pip-audit):

```
pip install -e ".[dev]"
```

## Run the smoke benchmark

```powershell
# Set a signing key (any string; use a real secret in CI)
$env:MLSEC_BENCH_SIGNING_KEY = "local-dev-key"

# Run smoke tests → JSON result
mlsec-benchmark run-smoke `
  --output results/smoke.json `
  --repository poojakira/mlsec-benchmark-suite `
  --repository-commit 0000000000000000000000000000000000000000 `
  --artifact-digest sha256:local `
  --model-hash sha256:none `
  --dependency-lock-hash sha256:local

# Validate the result (checks schema + signature)
mlsec-benchmark validate results/smoke.json --require-signature

# Generate a Markdown report from the result
mlsec-benchmark report results/smoke.json --output reports/smoke.md
```

On Linux/macOS, replace `$env:MLSEC_BENCH_SIGNING_KEY = "..."` with `export MLSEC_BENCH_SIGNING_KEY="..."` and use `\` for line continuation instead of backticks.

## How signing and integrity work

Every result file records immutable identifiers:

- **Repository commit** — which exact code produced the result
- **Artifact digest** — hash of the built package
- **Model hash** — hash of the model weights under test
- **Dataset hash** — hash of the test data
- **Configuration hash** — hash of the benchmark config
- **Dependency lock hash** — hash of the pinned dependency file
- **Environment and seeds** — so results can be reproduced

When `MLSEC_BENCH_SIGNING_KEY` is set, the CLI signs the result JSON with HMAC-SHA256. The `validate` command checks both the schema and the signature, so you can detect if anyone edited a result file after the fact.

The CLI also refuses to overwrite existing result files (unless you pass `--overwrite`), so historical results are preserved by default.

## Rules this project enforces

1. Results are generated from actual test runs, never typed by hand.
2. Failed runs are kept, not deleted.
3. Reports are generated from result JSON, not written manually.
4. Smoke, development, calibration, and final test datasets are tracked separately.

## Project structure

```
mlsec-benchmark-suite/
├── mlsec_benchmark_suite/   # CLI and core logic (stdlib only)
│   ├── cli.py               # Entry point
│   ├── contracts/           # Benchmark contract definitions
│   └── datasets/            # Fixture data for smoke tests
├── contracts/               # Published contract specs
├── datasets/                # Dataset manifests
├── schemas/                 # JSON schema for result validation
├── results/                 # Output directory for result JSON
├── reports/                 # Output directory for generated reports
└── tests/                   # pytest tests for the CLI itself
```

## Run tests

```
pytest
```

## License

Apache-2.0
