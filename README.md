# mlsec-benchmark-suite

Smoke-test infrastructure. Runs versioned fixture sets against portfolio tool adapters, produces structured JSON results. Regression checks only  -  not publishable benchmarks.

Adapters: `iam_lint_adapter`, `hf_scanner_adapter`, `prompt_injection_adapter`, `spectral_adapter`.

```bash
pip install -e ".[dev]" && pytest tests/ -q
```
