# Reproduce the Work — Poster 09

> Evidence status: This is a dated repository snapshot at the commit identified below. `VERIFIED_AT_SNAPSHOT` means verified for that commit and environment; it does not assert the same result on the latest `main`. Compare newer claims with the repository evidence before reuse.

**Repository:** `github.com/poojakira/mlsec-benchmark-suite` · Apache-2.0 • Python 3.12 • HEAD 848edf0506178f4e386c5007df9ae72001b5a238 • verified 2026-10-12

```
mlsec-benchmark run-hf-scanner --output r.json
pytest tests/
```

Evidence artifacts: CI run 38298946029 real-adapter job 114977020804 (historical results JSON is absent), METHODOLOGY.md, tests/


## Claim audit and rendered-source boundary, October 13, 2026 UTC

The reviewed printed claims, source and test commit anchors, CI dates and benchmark limitations are in `verified_claims.json`. The PDF is generated from that manifest and the PNG is rasterized from the same page by `render_poster.py`. Source inventory, dated CI and separate reported experiments must not be combined into one result. Earlier artifact versions remain in Git history; these corrections do not assert production readiness.

Offline poster rendering: `python -m pip install reportlab==4.4.9 PyMuPDF==1.26.6`, then `python poster/render_poster.py`. The font is bundled with the pinned ReportLab package; no browser or network fetch is used during rendering.

The genuine HF adapter requires the sibling scanner used by [real-adapter job 114977020804](https://github.com/poojakira/mlsec-benchmark-suite/actions/runs/38298946029/job/114977020804). Install this repository with `python -m pip install -e ".[dev]"`; install the documented `poojakira/hf-model-provenance-scanner` sibling at the exact checkout recorded in that job before running the real adapter. Do not substitute the mocked adapter test or claim a passing integration when the sibling is unavailable.

Exact dated real-adapter environment from job 114977020804:

```bash
python -m pip install -e ".[dev]"
python -m pip install "hf-scanner @ git+https://github.com/poojakira/hf-model-provenance-scanner.git@e0cb4018f40bfac51a783e9a7e194a4313e5246b"
pytest tests/test_hf_scanner_adapter.py::test_real_scanner_detects_all_bad_and_no_false_positives -v
```

This pins the actual sibling used by the cited fixture experiment; no latest-version equivalence is assumed.
