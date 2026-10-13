# Verified Metrics — Poster 09

> Evidence status: This is a dated repository snapshot at the commit identified below. `VERIFIED_AT_SNAPSHOT` means verified for that commit and environment; it does not assert the same result on the latest `main`. Compare newer claims with the repository evidence before reuse.

Apache-2.0 • Python 3.12 • HEAD 848edf0506178f4e386c5007df9ae72001b5a238 • verified 2026-10-12. Current README records Python 3.12 CI evidence.

## Headline cards
- 1.00 — HF-SCANNER F1
- 3/0 — TP / FP
Notes: run-hf-scanner: precision=recall=F1=1.0 on 5 committed fixtures. 3 known-bad flagged (HFS-024), 2 known-good clean. No mock.

## Verified surface
| Item | Value |
|---|---|
| Test functions | 83 across 10 modules |
| Current CI | 82 passed, 1 skipped |
| Statement coverage | 90.76% |
| Real fixtures | 5 |
| Real adapters | gated CI |

## Chart values
| Series | Value |
|---|---|
| Known-bad fixtures flagged | 3/3 |
| Known-good fixtures clean | 2/2 |
| Smoke scaffold | Not a measured detector score |
Note: Real adapter is end-to-end (no mock). Synthetic smoke output is schema plumbing, not a measured detector score; no smoke bar is rendered.

## Historical / provenance
run-hf-scanner imports the genuine scanner and reports actual findings. run-smoke's per-category numbers are seeded-PRNG synthetic, labeled as such.

## Not established by this repository
Real-world accuracy of any wrapped tool. That smoke- scaffold numbers mean anything beyond schema plumbing.


## Claim audit and rendered-source boundary, October 13, 2026 UTC

The reviewed printed claims, source and test commit anchors, CI dates and benchmark limitations are in `verified_claims.json`. The PDF is generated from that manifest and the PNG is rasterized from the same page by `render_poster.py`. Source inventory, dated CI and separate reported experiments must not be combined into one result. Earlier artifact versions remain in Git history; these corrections do not assert production readiness.

Offline poster rendering: `python -m pip install reportlab==4.4.9 PyMuPDF==1.26.6`, then `python poster/render_poster.py`. The font is bundled with the pinned ReportLab package; no browser or network fetch is used during rendering.
