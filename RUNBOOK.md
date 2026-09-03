# RUNBOOK — mlsec-benchmark-suite

Regression harness that imports each ML-security tool's Python module in-process,
runs it against versioned fixtures, and validates the output against a shared JSON
schema. This runbook documents every subcommand and its verified behavior.

## Prerequisites

- Python 3.10+
- The **unit tests** (`pytest tests/`) run fully with **no sibling tools installed**;
  adapter tests mock the sibling modules.
- A **live per-adapter benchmark** needs that adapter's sibling package importable:

  | Command | Requires (Python import) | Sibling repo |
  |---------|--------------------------|--------------|
  | `run-iam-lint` | `aws_agent_identity_guard` | `aws-agent-identity-guard` |
  | `run-hf-scanner` | `scanner.analyzer.config_scanner` | `hf-model-provenance-scanner` |
  | `run-prompt-injection` | `mcp_monitor.detectors.prompt_injection` | `mcp-agent-security-gateway` |
  | `run-spectral` | `poison_detector.spectral` + `numpy` | `dataset-poisoning-detector` |

  `run-smoke`, `validate`, `report`, and `build-index` require **no** sibling tools.

## Install

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The CLI entry point is `mlsec-benchmark` (registered via `[project.scripts]`);
`python -m mlsec_benchmark_suite ...` is equivalent.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | `run-all` completed but ≥1 adapter failed (unless `--allow-partial`) |
| 2 | Expected input error: schema validation failed, output file exists, missing file/key |
| 3 | A required sibling tool is not installed/importable (`dependency unavailable`) |

All non-zero exits print a one-line `error:` message to stderr — **no traceback**.

## Self-contained commands (no sibling tools)

### run-smoke (deterministic toy fixtures)

```bash
mlsec-benchmark run-smoke --output results/smoke.json \
  --repository-commit abc123 \
  --artifact-digest sha256:deadbeef \
  --model-hash sha256:cafebabe \
  --dependency-lock-hash sha256:feedface
# writes results/smoke.json (exit 0). Add --overwrite to replace an existing file.
```

### validate (requires a full-schema result)

```bash
mlsec-benchmark validate results/smoke.json
# validated results/smoke.json   (exit 0)
mlsec-benchmark validate results/smoke.json --require-signature
```

### report (Markdown, requires a full-schema result)

```bash
mlsec-benchmark report results/smoke.json --output reports/report.md
# writes a Markdown report (exit 0). Add --overwrite to replace.
```

### build-index (requires a directory of full-schema results)

```bash
mlsec-benchmark build-index --results-dir results --output results/index.json
```

### Ed25519 public-key signing (third-party verifiable)

Unlike the shared-secret HMAC path, an Ed25519 signature is verifiable by anyone
holding only the **public** key — no shared secret. Verified in this environment
(`cryptography` installed via `pip install -e ".[dev]"`):

```bash
mlsec-benchmark keygen-ed25519 --private-out key.pem --public-out key.pub.pem
mlsec-benchmark sign results/real_hf_scanner.json \
  --private-key key.pem --output results/real_hf_scanner.signed.json
mlsec-benchmark verify results/real_hf_scanner.signed.json            # uses embedded public key
mlsec-benchmark verify results/real_hf_scanner.signed.json --public-key key.pub.pem
# signature OK (ed25519) for results/real_hf_scanner.signed.json      (exit 0)
```

Tampering with any signed field, or verifying with the wrong public key, makes
`verify` exit 2 (`signature verification FAILED`). Signing keys (`*.pem`) are
git-ignored — never commit private keys.

### verify-dataset (checksum integrity gate)

Recomputes each committed fixture's SHA-256 and compares it to the checksums in
the dataset manifest, proving the benchmark ran against the exact committed data.

```bash
mlsec-benchmark verify-dataset \
  --manifest datasets/hf-scanner-fixtures.json --fixtures-dir fixtures/hf_configs
# dataset checksums OK: fixtures/hf_configs matches datasets/hf-scanner-fixtures.json  (exit 0)
```

The `run-hf-scanner` adapter runs this same integrity check automatically before
scoring, so a modified fixture aborts the run (exit 2) instead of producing a
result against unexpected data.

> **Important:** `validate`, `report`, and `build-index` require the full
> provenance schema written by `run-smoke` / `run-<adapter>`. `build-index`
> validates *every* `*.json` in `--results-dir`; if that directory contains a
> `run-all` aggregate file it will exit 2 with
> `error: result missing fields: [...]`. Point it at a directory that contains
> only full-schema results.

## Adapter benchmarks (need the matching sibling tool)

```bash
mlsec-benchmark run-iam-lint          --output results/iam_lint.json
mlsec-benchmark run-hf-scanner        --output results/hf_scanner.json
mlsec-benchmark run-prompt-injection  --output results/prompt_injection.json
mlsec-benchmark run-spectral          --output results/spectral.json
```

Verified in this environment (`aws-agent-identity-guard` and the real
`hf-scanner` sibling both installed):

```text
$ mlsec-benchmark run-iam-lint --output results/iam_lint.json
IAM lint benchmark complete: precision=1.0, recall=1.0, f1=1.0     # exit 0

$ mlsec-benchmark run-hf-scanner --output results/hf_scanner.json
HF scanner benchmark complete: precision=1.0, recall=1.0, f1=1.0   # exit 0 (REAL detector run)
```

The `run-hf-scanner` numbers above are a **REAL** run of the genuine
`scanner.analyzer.config_scanner.analyze_config_file` against the 5 committed
`fixtures/hf_configs/` files (3 known-bad, 2 known-good). When the sibling
scanner is **not** installed, `run-hf-scanner` exits with code 3:

```text
$ mlsec-benchmark run-hf-scanner --output results/hf_scanner.json
error: dependency unavailable: hf-model-provenance-scanner is not installed. Install with: pip install hf-model-provenance-scanner   # exit 3
```

`run-prompt-injection` and `run-spectral` behave identically to `run-hf-scanner`
when their siblings are absent (clean `error: dependency unavailable`, exit 3).

## run-all (aggregate across all four adapters)

```bash
mlsec-benchmark run-all --output results/combined.json
mlsec-benchmark run-all --output results/combined.json --allow-partial
```

`run-all` catches each adapter's failure internally and always writes an
**aggregate-only** combined file (`adapters_run`, `adapters_failed`, per-adapter
`results`). Verified output with only `aws-agent-identity-guard` installed:

```text
  iam-lint: f1=1.0
  hf-scanner: FAILED (hf-model-provenance-scanner is not installed. ...)
  prompt-injection: FAILED (mcp-agent-security-gateway is not installed. ...)
  spectral: FAILED (dataset-poisoning-detector is not installed. ...)

run-all complete: 1 adapters succeeded, 3 failed
```

Exit code: **1** by default when any adapter failed; **0** with `--allow-partial`.
The `combined.json` it writes is aggregate-only — do **not** pass it to
`validate`/`report`/`build-index` (see note above).

## Tests

```bash
pytest tests/ -q
# 67 passed              (with hf-scanner installed)
# 66 passed, 1 skipped   (without it — the real-detector test is skipped)
```

67 test functions across 8 modules: 4 adapter modules, `test_cli.py` (CLI dispatch,
clean-error exit codes 2 & 3, HMAC signing/tamper detection), `test_run_all.py`
(aggregate + partial-failure handling), `test_tracker.py` (trend/regression
analysis), and `test_signing_and_dataset.py` (Ed25519 keygen/sign/verify
round-trip, tamper + wrong-key detection, dataset checksum verification, and the
`--overwrite` warning). Sibling modules are mocked for the unit tests, so the
suite is green with no sibling tools installed. One test
(`test_hf_scanner_adapter.py::test_real_scanner_detects_all_bad_and_no_false_positives`)
runs the **real** hf-scanner detector end-to-end (no mock) and is skipped
automatically unless `hf-scanner` is installed; when installed it passes
(all counted in the 67).

```bash
pytest tests/test_cli.py -v            # single module
pytest tests/ -v --durations=10        # with timing
```

## Result JSON fields

| Field | Meaning |
|-------|---------|
| `results` | Per-category / per-adapter benchmark metrics |
| `aggregate_metrics` | Precision, recall, F1 per adapter |
| `signature` | Integrity signature: `unsigned` (SHA-256 digest only), `hmac-sha256` when `MLSEC_BENCH_SIGNING_KEY` is set, or `ed25519` (third-party verifiable public-key signature) after `mlsec-benchmark sign` |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `error: dependency unavailable` (exit 3) | Install the sibling package for that adapter (see Prerequisites table) |
| `error: result missing fields: [...]` (exit 2) | You passed a `run-all` aggregate to `validate`/`report`/`build-index`; use a `run-smoke` / per-adapter result |
| `refusing to overwrite existing artifact` (exit 2) | Add `--overwrite` |
| Signature verification fails | Set `MLSEC_BENCH_SIGNING_KEY` to the key used when the result was produced |
| Import errors during tests | Ensure the venv is activated and `pip install -e ".[dev]"` succeeded |
