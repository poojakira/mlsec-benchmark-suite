# Claim Ledger — Poster 09 (09-mlsec-benchmark-suite)

> Evidence status: This is a dated repository snapshot at the commit identified below. `VERIFIED_AT_SNAPSHOT` means verified for that commit and environment; it does not assert the same result on the latest `main`. Compare newer claims with the repository evidence before reuse.

MIT • Python 3.12 • HEAD 155f414188954be16d90f8e14370b81e5dde318e • verified 2026-10-01. Classification: VERIFIED_AT_SNAPSHOT / VERIFIED_HISTORICAL / PARTIAL / UNVERIFIED / UNSUPPORTED.

| # | Claim | Classification | Evidence |
|---|---|---|---|
| 1 | Real HF-scanner adapter: precision=recall=F1=1.0 on 5 fixtures | VERIFIED_AT_SNAPSHOT | README verified real run; tests/test_hf_scanner_adapter.py end-to-end (no mock); total_tp=3,total_fp=0,total_fn=0. |
| 2 | 73 test functions across 9 modules; 72 passed, 1 skipped; 88.34% statement coverage | VERIFIED_AT_SNAPSHOT | Current README/test evidence at HEAD 155f414188954be16d90f8e14370b81e5dde318e. |
| 3 | JSON-schema contracts + versioned fixtures; pytest fails on drift | VERIFIED_AT_SNAPSHOT | README how-it-works; schemas/ + contracts/ present. |
| 4 | run-smoke per-category numbers | UNSUPPORTED (disclaimed by repo) | README: seeded-PRNG synthetic scaffold for plumbing, NOT measurements. Shown as synthetic only. |
| 5 | Real-world accuracy of wrapped tools | UNSUPPORTED (disclaimed) | Suite validates contracts/format, not accuracy. |

## Policy applied
- Only VERIFIED_AT_SNAPSHOT figures appear as prominent current results.
- Historical/projected values are labeled (dashed box / explicit note).
- Unsupported production/accuracy claims are omitted or shown in the red "NOT ESTABLISHED" box.
