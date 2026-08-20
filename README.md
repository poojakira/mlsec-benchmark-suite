# mlsec-benchmark-suite

Pytest-based regression harness for the ML security portfolio. Wraps each tool's CLI/API in a typed adapter, runs it against versioned fixtures, and validates results against JSON schemas. Catches regressions before they ship.

## Adapters

| Adapter                    | Tool Under Test                   | Fixture Type       |
|---------------------------|-----------------------------------|--------------------|
| `iam_lint_adapter`        | aws-agent-identity-guard          | IAM policy JSON    |
| `hf_scanner_adapter`      | hf-model-provenance-scanner       | HF model configs   |
| `prompt_injection_adapter`| llm-redteam-framework classifier  | Prompt strings     |
| `spectral_adapter`        | dataset-poisoning-detector        | Poisoned datasets  |

## How It Works

1. Adapters invoke each tool against known-good and known-bad fixtures in `fixtures/`
2. Results are validated against `schemas/result.schema.json`
3. Contracts in `contracts/portfolio-smoke-v1.json` define expected pass/fail behavior
4. Structured JSON output goes to `results/`

## Usage

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all regression tests
pytest tests/ -q

# Run via CLI
python -m mlsec_benchmark_suite run --suite smoke
```

## Structure

```
mlsec_benchmark_suite/
  adapters/              4 tool adapters (~8-9 KB each)
  cli.py                 CLI entrypoint (run, report, validate)
  contracts/             Expected behavior definitions
  datasets/              Fixture set manifests
fixtures/
  iam_policies/          IAM policy test fixtures
  hf_configs/            HuggingFace config test fixtures
schemas/
  result.schema.json     JSON Schema for adapter output
tests/                   29 test functions across 6 test files
reports/                 Generated HTML reports
```

## Test Coverage

- 6 test modules: adapter-specific tests + CLI tests + integration (`test_run_all.py`)
- 29 test functions total
- Exercises all 4 adapters end-to-end

## Requirements

- Python 3.10+
- pytest
- Sibling repos installed (adapters shell out to their CLIs)

## License

Apache-2.0
