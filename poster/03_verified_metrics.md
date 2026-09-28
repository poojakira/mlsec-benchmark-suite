# Verified Metrics — Poster 09

> Evidence status: This is a dated repository snapshot at the commit identified below. `VERIFIED_AT_SNAPSHOT` means verified for that commit and environment; it does not assert the same result on the latest `main`. Compare newer claims with the repository evidence before reuse.

MIT • Python 3.12 • HEAD 7919488 • verified 2026-09-26. Verified for this poster on Windows / CPython 3.12.10.

## Headline cards
- 1.00 — HF-SCANNER F1
- 3/0 — TP / FP
Notes: run-hf-scanner: precision=recall=F1=1.0 on 5 committed fixtures. 3 known-bad flagged (HFS-024), 2 known-good clean. No mock.

## Verified surface
| Item | Value |
|---|---|
| Test functions | 70 |
| Real fixtures | 5 |
| Real adapters | gated CI |

## Chart values
| Series | Value |
|---|---|
| Known-bad flagged | 100 |
| Known-good clean | 100 |
| Smoke scaffold (synthetic) | 50 |
Note: Real adapter is end-to-end (no mock). Smoke bar marks synthetic plumbing, not a measurement.

## Historical / provenance
run-hf-scanner imports the genuine scanner and reports actual findings. run-smoke's per-category numbers are seeded-PRNG synthetic, labeled as such.

## Not established by this repository
Real-world accuracy of any wrapped tool. That smoke- scaffold numbers mean anything beyond schema plumbing.
