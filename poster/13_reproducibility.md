# Reproduce the Work — Benchmark Suite Poster 09

**Historical code snapshot:** `5c20f1da9602eb162efe8c63158da52b11d61f60` (October 1, 2026)  
**Historical license at that commit:** **Apache License 2.0**, verified against its `LICENSE` file. Later versions may carry proprietary terms; historical grants remain applicable.

```bash
git clone https://github.com/poojakira/mlsec-benchmark-suite.git
cd mlsec-benchmark-suite
git checkout 5c20f1da9602eb162efe8c63158da52b11d61f60
python -m pip install -e ".[dev]"
pytest tests/ -q
```

Historical evidence: **82 passed, 1 skipped** (83 collected), **90.07% statement coverage**, 83 test functions across 10 modules. A separately run genuine HF scanner adapter yielded 3 true positives and 0 false positives on five committed fixtures; it does not prove real-world detection accuracy. A smoke scaffold uses synthetic PRNG numbers, not measurements.

The poster graphic is regenerated from the research brief and verified metrics, and must be checked against the final PR head.
