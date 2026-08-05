# mlsec-benchmark-suite

[![Live Dashboard](https://img.shields.io/badge/Live_Dashboard-View-blue)](https://poojakira.github.io/mlsec-benchmark-suite/)

A deterministic smoke-test harness for testing benchmark contracts, result schemas, and evidence-signing workflows.

It runs smoke tests that exercise the pipeline end-to-end: run tests, validate results against a JSON schema, sign results with HMAC-SHA256, and generate a Markdown report. Smoke tests prove the tooling works — they are **not** product performance claims.

**Current state:** Smoke tests only. Full benchmark datasets and product-specific adapters connecting real detectors are not yet implemented. Commit hashes and artifact hashes are accepted as user-provided strings and validated for non-emptiness, not verified against real artifacts. Signing uses shared-secret HMAC rather than independently verifiable public-key signing.

## What works today

- CLI smoke benchmark that exercises the schema, signing, and report pipeline end-to-end
- HMAC-SHA256 result signing with the `validate` command for tamper detection
- Markdown report generation from result JSON
- Deterministic pseudorandom result values for smoke runs (not real detector metrics)

## What's planned

- Public benchmark datasets for each product area
- Product-specific adapters that connect real detectors (hf-scanner, mcp-monitor, llm-redteam, etc.) to the benchmark contracts
- Calibration and final-test dataset splits
- Comparative reporting (without comparisons to commercial products unless independently reproducible)
- Migration to public-key signing for independently verifiable evidence

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

- **Repository commit** - which exact code produced the result
- **Artifact digest** - hash of the built package
- **Model hash** - hash of the model weights under test
- **Dataset hash** - hash of the test data
- **Configuration hash** - hash of the benchmark config
- **Dependency lock hash** - hash of the pinned dependency file
- **Environment and seeds** - so results can be reproduced

When `MLSEC_BENCH_SIGNING_KEY` is set, the CLI signs the result JSON with HMAC-SHA256. The `validate` command checks both the schema and the signature, so you can detect if anyone edited a result file after the fact.

The CLI also refuses to overwrite existing result files (unless you pass `--overwrite`), so historical results are preserved by default.

**Note on current signing limitations:** HMAC-SHA256 with a shared secret confirms the file has not been edited since signing, but it does not provide independent third-party verifiability (the same key that signs can also forge). Public-key signing is planned.

## Rules this project enforces

1. Results are generated from actual test runs, never typed by hand.
2. Failed runs are kept, not deleted.
3. Reports are generated from result JSON, not written manually.
4. Smoke, development, calibration, and final test datasets are tracked separately.

## Project structure

```
mlsec-benchmark-suite/
  cli.py            - CLI entry point (run-smoke, validate, report)
  schema/           - JSON schema for result files
  signing/          - HMAC signing and verification
  smoke/            - Smoke test runner (deterministic pseudorandom results)
  adapters/         - Placeholder: real detector adapters (not yet implemented)
  reports/          - Report generator
tests/
  test_smoke.py     - Smoke benchmark pipeline tests
  test_schema.py    - Result schema validation tests
  test_signing.py   - Signing and verification tests
```

## License

MIT
