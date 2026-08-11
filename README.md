# ML Security Benchmark Suite

Smoke-test and evidence infrastructure for the ML security portfolio. The suite runs small, versioned fixture sets and produces structured JSON results conforming to `schemas/result.schema.json`.

This is not a full production benchmark suite. Current adapters are regression checks for known fixtures and should not be used to claim real-world detection rates, false-positive rates, or product superiority.

## Install

```powershell
git clone https://github.com/poojakira/mlsec-benchmark-suite.git
cd mlsec-benchmark-suite
py -m pip install -e ".[dev]"
py -m pip install -e ../aws-agent-identity-guard
```

## Run Benchmarks

```powershell
py -m mlsec_benchmark_suite run-all --output results.json
py -m mlsec_benchmark_suite run-iam-lint --output iam_results.json
```

`run-iam-lint` requires `aws-agent-identity-guard`. In this portfolio workspace the adapter can also import it from a sibling checkout at `../aws-agent-identity-guard/src`.

## Available Adapters

| Adapter | Tool | What It Benchmarks |
|---------|------|--------------------|
| `iam_lint_adapter` | aws-agent-identity-guard | IAM policy lint rules against committed fixture policies |
| `hf_scanner_adapter` | hf-model-provenance-scanner | Smoke fixtures for model config scanning |
| `prompt_injection_adapter` | llm-redteam-framework | Smoke fixtures for prompt-injection detection |
| `spectral_adapter` | adversarial-ml-lab | Smoke fixtures for spectral-signature checks |

## Run Tests

```powershell
py -m pytest tests/ -q
```

Expected result depends on the installed optional adapters. If an adapter dependency is missing, install the sibling package or run the targeted tests for installed adapters.

## Project Structure

```
mlsec_benchmark_suite/
├── adapters/         # Tool-specific benchmark adapters
├── contracts/        # Benchmark contract definitions
├── datasets/         # Fixture data for benchmark runs
├── cli.py            # CLI entry point (run-all, run-iam-lint, etc.)
└── __main__.py       # Module entry point
```

## Output Format

Results follow the schema in `schemas/result.schema.json` and include:
- Tool name and version
- Fixture set used
- Pass/fail per test case
- Aggregate metrics for fixture regression only

Do not publish these metrics as external benchmark results without a documented corpus, provenance, baseline, environment, and raw result artifact.
