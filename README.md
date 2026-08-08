# ML Security Benchmark Suite

Automated benchmarking framework for all portfolio ML security tools. Runs each tool against standardized fixture sets and produces structured JSON results conforming to `schemas/result.schema.json`.

## Install

```powershell
git clone https://github.com/poojakira/mlsec-benchmark-suite.git
cd mlsec-benchmark-suite
py -m pip install -e ".[dev]"
py -m pip install aws-agent-identity-guard
```

## Run Benchmarks

```powershell
py -m mlsec_benchmark_suite run-all --output results.json
py -m mlsec_benchmark_suite run-iam-lint --output iam_results.json
```

## Available Adapters

| Adapter | Tool | What It Benchmarks |
|---------|------|--------------------|
| `iam_lint_adapter` | aws-agent-identity-guard | IAM policy lint rules against fixture policies |
| `hf_scanner_adapter` | hf-model-provenance-scanner | Model config scanning accuracy |
| `prompt_injection_adapter` | llm-redteam-framework | Prompt injection detection rates |
| `spectral_adapter` | adversarial-ml-lab | Spectral signature detection |

## Run Tests

```powershell
py -m pytest tests/ -q
```

Expected: 28 passed

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
- Aggregate metrics (precision, recall, F1, timing)
