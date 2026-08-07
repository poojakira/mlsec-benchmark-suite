# mlsec-benchmark-suite

## 🚧 PRE-ALPHA — Benchmark infrastructure only, no real measurements yet

This repo contains **benchmark plumbing** — schema validation, HMAC signing, report generation, and a CLI harness. It does **not** produce real security metrics. No actual benchmark adapters connect to real detectors.

---

## What actually exists

- A CLI (`mlsec-benchmark`) that runs deterministic **smoke tests** with pseudorandom values
- JSON schema validation for result files
- HMAC-SHA256 signing and verification of result files
- Markdown report generation from result JSON

**All metric values are fake.** The smoke tests prove the pipeline (run → validate → report) works end-to-end. They exercise the contract, not real detectors.

There are no adapters that invoke `hf-model-provenance-scanner`, `mcp-security-gateway-monitor`, `llm-redteam-framework`, or any other real detector. The `adapters/` directory is an empty placeholder.

---

## What the HMAC signing infrastructure is for

The signing system exists so that when real benchmarks eventually run, their results can be:

1. **Tamper-evident** — HMAC-SHA256 signs the full result JSON. The `validate` command detects any post-hoc edits to metric values, commit hashes, or metadata.
2. **Traceable** — Each result records the repository commit, artifact digest, model hash, dataset hash, dependency lock hash, and random seeds, so a measurement can be tied back to a specific reproducible state.
3. **Append-only** — The CLI refuses to overwrite existing results (unless `--overwrite` is passed), preserving history.

**Current limitation:** HMAC uses a shared secret. Anyone with the key can both sign and forge. This proves the file hasn't been edited since signing, but does not provide independent third-party verifiability. Public-key signing is planned but not implemented.

---

## What would need to happen to make this useful

To move from infrastructure smoke tests to real measurements:

1. **Write detector adapters** — Implement adapters in `adapters/` that invoke real detectors (e.g., `hf-model-provenance-scanner`, `mcp-security-gateway-monitor`, `llm-redteam-framework`, `dataset-poisoning-detector`) and translate their outputs into the benchmark result schema.
2. **Curate benchmark datasets** — Assemble labeled test sets for each detector: known-malicious models, attack catalogs, poisoned training data, adversarial examples. Separate calibration splits from final-test splits.
3. **Run against real detectors** — Execute the adapters against the benchmark datasets, producing genuine precision/recall/F1/latency numbers instead of pseudorandom values.
4. **Migrate to public-key signing** — Replace HMAC with asymmetric signatures so third parties can independently verify results without access to the signing key.
5. **Publish reproducibility instructions** — Document exact environment, dependency versions, and seeds so anyone can replicate a benchmark run.

Until steps 1–3 are complete, **this repo produces zero real security measurements**.

---

## Install

Requires Python 3.10+. No runtime dependencies beyond the standard library.

```bash
git clone https://github.com/poojakira/mlsec-benchmark-suite
cd mlsec-benchmark-suite
pip install -e ".[dev]"
```

## Run the smoke tests

```bash
export MLSEC_BENCH_SIGNING_KEY="local-dev-key"

mlsec-benchmark run-smoke \
  --output results/smoke.json \
  --repository poojakira/mlsec-benchmark-suite \
  --repository-commit 0000000000000000000000000000000000000000 \
  --artifact-digest sha256:local \
  --model-hash sha256:none \
  --dependency-lock-hash sha256:local

mlsec-benchmark validate results/smoke.json --require-signature
mlsec-benchmark report results/smoke.json --output reports/smoke.md
```

On Windows PowerShell, use `$env:MLSEC_BENCH_SIGNING_KEY = "local-dev-key"` and backticks for line continuation.

---

## License

Apache-2.0
