# ML Security Benchmark Suite

Independent benchmark and evidence infrastructure for the `poojakira` ML security portfolio. Product repositories must not hardcode flattering scores; they should publish immutable artifacts that this suite can validate and report.

## What This Provides

- Versioned benchmark contracts for HF scanner, MCP gateway, LLM detector, dataset-poisoning detector, model-privacy attacks, adversarial robustness, and PulseNet.
- Dataset manifests with source, license, version, checksum, acquisition procedure and split policy.
- Required immutable identifiers: repository commit, artifact digest, model hash, dataset hash, configuration hash, dependency lock hash, environment and seeds.
- Machine-readable JSON results and generated Markdown reports.
- Raw smoke outputs embedded in the result manifest; full benchmarks must retain legally permitted raw artifacts separately.
- HMAC-SHA256 result signatures when `MLSEC_BENCH_SIGNING_KEY` is configured.
- Schema validation that rejects incomplete evidence.
- CI smoke benchmarks distinct from future full benchmarks.

## Smoke Benchmark

```powershell
$env:MLSEC_BENCH_SIGNING_KEY = "local-dev-key"
py -3.12 -m mlsec_benchmark_suite.cli run-smoke `
  --output results/smoke.json `
  --repository poojakira/mlsec-benchmark-suite `
  --repository-commit 0000000000000000000000000000000000000000 `
  --artifact-digest sha256:local `
  --model-hash sha256:none `
  --dependency-lock-hash sha256:local
py -3.12 -m mlsec_benchmark_suite.cli validate results/smoke.json --require-signature
py -3.12 -m mlsec_benchmark_suite.cli report results/smoke.json --output reports/smoke.md
```

Smoke results are deterministic for fixed inputs and seeds. They are not product performance claims.

## Evidence Rules

- Do not overwrite historical results. The CLI refuses to overwrite outputs unless `--overwrite` is explicit.
- Record failed runs and retain them.
- Distinguish smoke, development, calibration and final test sets in dataset manifests.
- Do not compare against commercial products unless testing is authorized and independently reproducible.
- Reports must be generated from raw result JSON, not manually typed metrics.

## Current Limitations

This initial repository ships CI smoke contracts and plumbing. Full public benchmark datasets and product-specific adapters still need to be added before portfolio metrics can be published.
