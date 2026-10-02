# Research Brief — Poster 09

> Evidence status: This is a dated repository snapshot at the commit identified below. `VERIFIED_AT_SNAPSHOT` means verified for that commit and environment; it does not assert the same result on the latest `main`. Compare newer claims with the repository evidence before reuse.

## Repository
`github.com/poojakira/mlsec-benchmark-suite` (public, default branch `main`, primary language Python). MIT • Python 3.12 • HEAD 5c20f1da9602eb162efe8c63158da52b11d61f60 • verified 2026-10-01

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
- **VERIFIED_AT_SNAPSHOT** — Real HF-scanner adapter: precision=recall=F1=1.0 on 5 fixtures — README verified real run; tests/test_hf_scanner_adapter.py end-to-end (no mock); total_tp=3,total_fp=0,total_fn=0.
- **VERIFIED_AT_SNAPSHOT** — 83 test functions across 10 test modules; current Python 3.12 CI recorded 82 passed, 1 skipped with 90.07% statement coverage — repository README and test tree at HEAD 5c20f1da9602eb162efe8c63158da52b11d61f60.
- **VERIFIED_AT_SNAPSHOT** — JSON-schema contracts + versioned fixtures; pytest fails on drift — README how-it-works; schemas/ + contracts/ present.
- **UNSUPPORTED (disclaimed by repo)** — run-smoke per-category numbers — README: seeded-PRNG synthetic scaffold for plumbing, NOT measurements. Shown as synthetic only.
- **UNSUPPORTED (disclaimed)** — Real-world accuracy of wrapped tools — Suite validates contracts/format, not accuracy.

## Important Negative / Honest Results
See RESULTS panel: Real adapter is end-to-end (no mock). Smoke bar marks synthetic plumbing, not a measurement.

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
Evidence: results/real_hf_scanner.json, METHODOLOGY.md, tests/

## References
[1] JSON Schema · [2] pytest · [3] OWASP ML Security · [4] MITRE ATLAS · [5] SLSA / evidence provenance · [6] NIST AI RMF 1.0
