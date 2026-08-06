# Security Audit — mlsec-benchmark-suite

**Date:** 2026-08-06  
**Classification:** SMOKE-TEST HARNESS — not a production benchmark platform

---

## Critical Findings

### CRITICAL-1: Pseudorandom metrics presented as real results

**Files:** Any generated output from the harness  
**Issue:** If the suite generates random numbers and labels them as security metrics (AUROC, F1, detection rate), this is fundamentally misleading.  
**Status:** README already clarifies "smoke-test harness" naming.  
**Remediation:** All output must include `"_synthetic": true` field and prominent notice.

---

## Medium Findings

### M-01: No dependabot.yml
**Status:** Added in this PR.

### M-02: No real adapter implementations
**Status:** Adapter interface exists but implementations are stubs.

---

## Unsupported Claims

| Claim | Status |
|-------|--------|
| "Immutable signed evidence" | NOT IMPLEMENTED — renamed to smoke-test harness |
| Real benchmark adapters | STUBS ONLY — no real model evaluation |
| Cross-benchmark comparison | NOT IMPLEMENTED |

---

## Evidence Classification

All outputs from this tool are `SYNTHETIC_SMOKE_RESULT` unless connected to a real model checkpoint and dataset.
