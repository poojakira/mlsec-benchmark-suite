# Claim Ledger — Poster 09 (09-mlsec-benchmark-suite)

> Evidence status: This is a dated repository snapshot at the commit identified below. `VERIFIED_AT_SNAPSHOT` means verified for that commit and environment; it does not assert the same result on the latest `main`. Compare newer claims with the repository evidence before reuse.

Apache-2.0 • Python 3.12 • HEAD 848edf0506178f4e386c5007df9ae72001b5a238 • verified 2026-10-12. Classification: VERIFIED_AT_SNAPSHOT / VERIFIED_HISTORICAL / PARTIAL / UNVERIFIED / UNSUPPORTED.

| # | Claim | Classification | Evidence |
|---|---|---|---|
| 1 | Real HF-scanner adapter: precision=recall=F1=1.0 on 5 fixtures | VERIFIED_AT_SNAPSHOT | CI run 38298946029 real-adapter job 114977020804; tests/test_hf_scanner_adapter.py end-to-end (no mock); total_tp=3,total_fp=0,total_fn=0. |
| 2 | 83 test functions across 10 modules; 82 passed, 1 skipped; 90.76% statement coverage | VERIFIED_AT_SNAPSHOT | Current README/test evidence at HEAD 848edf0506178f4e386c5007df9ae72001b5a238. |
| 3 | JSON-schema contracts + versioned fixtures; pytest fails on drift | VERIFIED_AT_SNAPSHOT | README how-it-works; schemas/ + contracts/ present. |
| 4 | run-smoke per-category numbers | UNSUPPORTED (disclaimed by repo) | README: seeded-PRNG synthetic scaffold for plumbing, NOT measurements. Shown as synthetic only. |
| 5 | Real-world accuracy of wrapped tools | UNSUPPORTED (disclaimed) | Suite validates contracts/format, not accuracy. |

## Policy applied
- Only VERIFIED_AT_SNAPSHOT figures appear as prominent current results.
- Historical/projected values are labeled (dashed box / explicit note).
- Unsupported production/accuracy claims are omitted or shown in the red "NOT ESTABLISHED" box.


## Claim audit and rendered-source boundary, October 13, 2026 UTC

The reviewed printed claims, source and test commit anchors, CI dates and benchmark limitations are in `verified_claims.json`. The PDF is generated from that manifest and the PNG is rasterized from the same page by `render_poster.py`. Source inventory, dated CI and separate reported experiments must not be combined into one result. Earlier artifact versions remain in Git history; these corrections do not assert production readiness.

Offline poster rendering: `python -m pip install reportlab==4.4.9 PyMuPDF==1.26.6`, then `python poster/render_poster.py`. The font is bundled with the pinned ReportLab package; no browser or network fetch is used during rendering.
