# Research Brief — Poster 09

> Evidence status: This is a dated repository snapshot at the commit identified below. `VERIFIED_AT_SNAPSHOT` means verified for that commit and environment; it does not assert the same result on the latest `main`. Compare newer claims with the repository evidence before reuse.

## Repository
`github.com/poojakira/mlsec-benchmark-suite` (public, default branch `main`, primary language Python). Apache-2.0 • Python 3.12 • HEAD 848edf0506178f4e386c5007df9ae72001b5a238 • verified 2026-10-12

## Academic Project Title
**Reproducible Regression Harness for Machine-Learning Security Tools**

### Subtitle
Contract-Validated Adapters Catching Cross-Repo Breakage Before It Ships

## One-Sentence Contribution
A contract-validated regression harness that wraps ML security tools in typed in-process adapters, runs them against versioned fixtures, and fails pytest on schema drift — with a hard, labeled separation between REAL product adapters and a synthetic smoke-test scaffold.

## Problem Statement
Several ML security tools live in separate repos. Each passes its own tests in isolation. When one changes its output format, downstream consumers break silently — missing findings surface weeks later. A shared harness with typed adapters and JSON-schema contracts turns silent drift into an immediate failure.

## Threat Model
Chain: TOOL OUTPUT CHANGE -> DOWNSTREAM CONSUMER -> MISSING FINDINGS -> CONTRACT BOUNDARY -> PYTEST FAIL FAST.
Adversary capability: n/a — integrity/ regression risk; Assumptions: tools importable in- process; frozen fixtures; Out of scope: real-world accuracy; smoke-test scaffold numbers are synthetic; Residual risk: fixture coverage gaps; adapter staleness.

## Research / Engineering Question
> Can independently-developed ML security tools be held to shared output contracts so cross-repo format drift fails fast instead of silently?

## Objective
Determine whether typed adapters + JSON-schema contracts over frozen fixtures can catch cross-repo output drift in a single pytest run.

## Engineering Sub-Objectives
O1 — In-process typed adapters
O2 — Versioned known-good/bad fixtures
O3 — JSON-schema output validation
O4 — Real adapter gating in CI

## Methodology
1 Load (fixtures) -> 2 Adapt (in-proc) -> 3 Run (tool) -> 4 Validate (schema) -> 5 Assert (contract) -> 6·7 Report (Markdown)

## Evidence at Poster Snapshot + Claim Ledger
- **VERIFIED_AT_SNAPSHOT** — Real HF-scanner adapter: precision=recall=F1=1.0 on 5 fixtures — CI run 38298946029 real-adapter job 114977020804; tests/test_hf_scanner_adapter.py end-to-end (no mock); total_tp=3,total_fp=0,total_fn=0.
- **VERIFIED_AT_SNAPSHOT** — 83 test functions across 10 test modules; current Python 3.12 CI recorded 82 passed, 1 skipped with 90.76% statement coverage — repository README and test tree at HEAD 848edf0506178f4e386c5007df9ae72001b5a238.
- **VERIFIED_AT_SNAPSHOT** — JSON-schema contracts + versioned fixtures; pytest fails on drift — README how-it-works; schemas/ + contracts/ present.
- **UNSUPPORTED (disclaimed by repo)** — run-smoke per-category numbers — README: seeded-PRNG synthetic scaffold for plumbing, NOT measurements. Shown as synthetic only.
- **UNSUPPORTED (disclaimed)** — Real-world accuracy of wrapped tools — Suite validates contracts/format, not accuracy.

## Important Negative / Honest Results
See RESULTS panel: Real adapter is end-to-end (no mock). Synthetic smoke output is schema plumbing, not a measured detector score; no smoke bar is rendered.

## Limitations
1. Validates contracts/format, not real-world accuracy.
2. run-smoke numbers are synthetic (seeded PRNG).
3. Fixture coverage is finite; gaps possible.
4. Adapters can go stale if a tool changes internals.
5. Real adapter gating requires sibling install.

## Future Work
• More REAL adapters (iam-lint, spectral, injection).
• Expanded fixture corpora per tool.
• Cross-tool pipeline contracts.
• Signed evidence provenance chain.
• Coverage reporting per adapter.

## Reproducibility
```
mlsec-benchmark run-hf-scanner --output r.json
pytest tests/
```
Evidence: CI run 38298946029 real-adapter job 114977020804 (historical results JSON is absent), METHODOLOGY.md, tests/

## References
[1] JSON Schema · [2] pytest · [3] OWASP ML Security · [4] Apache-2.0RE ATLAS · [5] SLSA / evidence provenance · [6] NIST AI RMF 1.0


## Claim audit and rendered-source boundary, October 13, 2026 UTC

The reviewed printed claims, source and test commit anchors, CI dates and benchmark limitations are in `verified_claims.json`. The PDF is generated from that manifest and the PNG is rasterized from the same page by `render_poster.py`. Source inventory, dated CI and separate reported experiments must not be combined into one result. Earlier artifact versions remain in Git history; these corrections do not assert production readiness.

Offline poster rendering: `python -m pip install reportlab==4.4.9 PyMuPDF==1.26.6`, then `python poster/render_poster.py`. The font is bundled with the pinned ReportLab package; no browser or network fetch is used during rendering.
