# Claim Ledger — Poster 09 (09-mlsec-benchmark-suite)

MIT • Python 3.12 • HEAD 78b4667 • verified 2026-09-26. Classification: VERIFIED_CURRENT / VERIFIED_HISTORICAL / PARTIAL / UNVERIFIED / UNSUPPORTED.

| # | Claim | Classification | Evidence |
|---|---|---|---|
| 1 | Real HF-scanner adapter: precision=recall=F1=1.0 on 5 fixtures | VERIFIED_CURRENT | README verified real run; tests/test_hf_scanner_adapter.py end-to-end (no mock); total_tp=3,total_fp=0,total_fn=0. |
| 2 | 70 test functions across suite | VERIFIED_CURRENT | Counted def test_ in tests/ (HEAD 78b4667). |
| 3 | JSON-schema contracts + versioned fixtures; pytest fails on drift | VERIFIED_CURRENT | README how-it-works; schemas/ + contracts/ present. |
| 4 | run-smoke per-category numbers | UNSUPPORTED (disclaimed by repo) | README: seeded-PRNG synthetic scaffold for plumbing, NOT measurements. Shown as synthetic only. |
| 5 | Real-world accuracy of wrapped tools | UNSUPPORTED (disclaimed) | Suite validates contracts/format, not accuracy. |

## Policy applied
- Only VERIFIED_CURRENT figures appear as prominent current results.
- Historical/projected values are labeled (dashed box / explicit note).
- Unsupported production/accuracy claims are omitted or shown in the red "NOT ESTABLISHED" box.
