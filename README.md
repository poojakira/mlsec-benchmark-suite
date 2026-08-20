# mlsec-benchmark-suite

Smoke-test harness for the ML security portfolio. Runs versioned fixture sets against adapters for each tool, produces structured JSON results. Used for regression checks — not publishable benchmarks.

## What It Does

Adapters wrap each portfolio tool's CLI or API and run them against known-good/known-bad fixture files:

- `iam_lint_adapter` — tests aws-agent-identity-guard rules against IAM policy fixtures
- `hf_scanner_adapter` — tests hf-model-provenance-scanner against model config fixtures
- `prompt_injection_adapter` — tests llm-redteam-framework classifier against prompt fixtures
- `spectral_adapter` — tests API spec linting

## Structure

```
mlsec_benchmark_suite/
  adapters/          - Wrapper code for each tool
  cli.py             - CLI entrypoint
  contracts/         - Expected result schemas
  datasets/          - Fixture definitions
fixtures/            - Test input files (IAM policies, HF configs)
schemas/             - JSON schema for result format
tests/               - Unit tests for adapters
```

## Usage

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

## Status

Works locally for regression testing during development. Adapters expect sibling repos to be installed.
