# ML Security Benchmark Suite

Automated benchmarking across all portfolio security tools. Runs real detector adapters against labeled fixtures and synthetic data, producing reproducible precision/recall/F1 metrics with HMAC-signed result files.

---

## Available Adapters

| Adapter | Tool Under Test | Method |
|---------|----------------|--------|
| `iam-lint` | [aws-agent-identity-guard](https://github.com/poojakira/aws-agent-identity-guard) | IAM policy fixtures with known rule violations |
| `hf-scanner` | [hf-model-provenance-scanner](https://github.com/poojakira/hf-model-provenance-scanner) | Model config fixtures (known-good vs known-bad) |
| `prompt-injection` | [mcp-security-gateway-monitor](https://github.com/poojakira/mcp-security-gateway-monitor) | Injection strings vs benign strings |
| `spectral` | [dataset-poisoning-detector](https://github.com/poojakira/dataset-poisoning-detector) | Synthetic 2-Gaussian poisoned data (5% label flips) |

---

## Usage

### Run all benchmarks

```bash
python -m mlsec_benchmark_suite run-all --output results.json
```

### Run individual adapters

```bash
# IAM policy lint
mlsec-benchmark run-iam-lint --output results/iam.json

# HuggingFace model config scanner
mlsec-benchmark run-hf-scanner --output results/hf.json

# Prompt injection detection
mlsec-benchmark run-prompt-injection --output results/prompt.json

# Spectral poisoning detection
mlsec-benchmark run-spectral --output results/spectral.json
```

### Smoke tests (deterministic pipeline validation)

```bash
export MLSEC_BENCH_SIGNING_KEY="local-dev-key"

mlsec-benchmark run-smoke \
  --output results/smoke.json \
  --repository poojakira/mlsec-benchmark-suite \
  --repository-commit $(git rev-parse HEAD) \
  --artifact-digest sha256:local \
  --model-hash sha256:none \
  --dependency-lock-hash sha256:local

mlsec-benchmark validate results/smoke.json --require-signature
mlsec-benchmark report results/smoke.json --output reports/smoke.md
```

On Windows PowerShell, use `$env:MLSEC_BENCH_SIGNING_KEY = "local-dev-key"` and backticks for line continuation.

---

## Install

Requires Python 3.10+.

```bash
git clone https://github.com/poojakira/mlsec-benchmark-suite
cd mlsec-benchmark-suite
pip install -e ".[dev]"
```

Adapter-specific dependencies (install the tools you want to benchmark):

```bash
pip install aws-agent-identity-guard       # for iam-lint adapter
pip install hf-model-provenance-scanner    # for hf-scanner adapter
pip install mcp-security-gateway-monitor   # for prompt-injection adapter
pip install dataset-poisoning-detector numpy  # for spectral adapter
```

---

## Result Integrity

- **HMAC-SHA256 signing** — result files are tamper-evident
- **Input identity tracking** — each result records repository commit, artifact digest, model hash, dataset hash, dependency lock hash, and seeds
- **Append-only** — CLI refuses to overwrite existing results unless `--overwrite` is passed
- **Reproducible** — fixed seeds and committed fixtures ensure deterministic results

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q
ruff check .
```

---

## License

Apache-2.0
