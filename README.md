# mlsec-benchmark-suite

Regression harness that runs multiple ML security tools against versioned fixtures and catches cross-repo breakage before it ships.

---

## What Problem This Solves

I maintain several ML security tools in separate repos. Each has its own tests, and each passes in isolation. But when one tool changes its output format, downstream tools that consume that output break silently. You don't find out until someone notices missing findings weeks later.

This suite wraps each tool's CLI in a typed adapter, runs it against frozen inputs, and validates outputs against a shared JSON schema. If any tool drifts from its contract, `pytest` fails immediately. One command tells you whether the portfolio still works as a whole.

---

## How It Works

- Typed adapters wrap each tool's CLI interface
- Versioned fixtures provide known-good and known-bad inputs
- Contracts define expected pass/fail behavior per fixture
- JSON Schema validation ensures output format consistency
- A single `pytest` run exercises all tools and produces HTML reports

Adding a new tool means writing one adapter file and dropping fixtures into the right directory. No infrastructure changes needed.

---

## Architecture Overview

```
+------------------+     +------------------+     +------------------+
|   CLI / pytest   |---->|    Adapters (4)   |---->|  Tools Under Test |
|   entrypoint     |     |  typed wrappers   |     |  (sibling repos)  |
+------------------+     +------------------+     +------------------+
        |                        |
        v                        v
+------------------+     +------------------+
|    Contracts     |     |  Versioned       |
|  (expected       |     |  Fixtures        |
|   pass/fail)     |     |  (known inputs)  |
+------------------+     +------------------+
        |                        |
        v                        v
+------------------+     +------------------+
|  JSON Schema     |     |  Results (JSON)  |
|  Validation      |     |  + HTML Reports  |
+------------------+     +------------------+
        |
        v
+------------------+
|    Dashboard     |
|  (GitHub Pages)  |
+------------------+
```

Component responsibilities:

| Component | What it does |
|-----------|-------------|
| `mlsec_benchmark_suite/adapters/` | Typed Python wrappers (one per tool) that invoke each tool's CLI and normalize the output into a common structure. Each adapter is roughly 8-9 KB of focused integration code. |
| `mlsec_benchmark_suite/cli.py` | CLI entrypoint exposing `run`, `report`, and `validate` subcommands. |
| `contracts/portfolio-smoke-v1.json` | Declares which fixtures should pass and which should fail for each adapter. This is the source of truth for expected behavior. |
| `fixtures/` | Versioned input files (IAM policy JSON, HuggingFace model configs, prompt strings, poisoned datasets) that tools are tested against. |
| `schemas/result.schema.json` | JSON Schema that every adapter output must validate against. Enforces structural consistency across the portfolio. |
| `results/` | Structured JSON output from each benchmark run. Machine-readable for downstream analysis. |
| `reports/` | Generated HTML reports for human review. |
| `dashboard/` | Static HTML page served via GitHub Pages for at-a-glance status. |
| `datasets/` | Fixture set manifests describing which inputs belong to which test suites. |
| `tests/` | 54 test functions across 7 test modules covering all adapters, CLI, and integration. |

---

## End-to-End Workflow: How Benchmarks Run

1. **Invoke**: You run `pytest tests/ -q` or `python -m mlsec_benchmark_suite run --suite smoke`. The CLI (or pytest) discovers all registered adapters.

2. **Load contracts**: The runner reads `contracts/portfolio-smoke-v1.json` to determine which fixtures to feed each adapter and what the expected outcome should be (pass or fail).

3. **Execute adapters**: Each adapter shells out to its corresponding tool's CLI (e.g., `iam_lint_adapter` calls `aws-agent-identity-guard`), passing the appropriate fixture files from `fixtures/`.

4. **Capture output**: Adapter normalizes the tool's stdout/stderr into a structured JSON result object.

5. **Validate schema**: Each result is validated against `schemas/result.schema.json`. If the tool's output format has drifted, validation fails immediately.

6. **Check contract**: The result (pass/fail/findings count) is compared against the contract's expected behavior. A mismatch is a test failure.

7. **Write results**: Structured JSON goes to `results/`. If running in report mode, an HTML summary is generated in `reports/`.

8. **CI gate**: In GitHub Actions, a non-zero exit code from pytest blocks the merge.

---

## Design Decisions and Trade-offs

**Adapters shell out to CLIs rather than importing Python modules directly.**
Why: The tools under test may be written in different languages, may have conflicting dependencies, or may change their internal APIs without notice. Shelling out to the CLI treats each tool as a black box with a stable interface (its command-line contract). The trade-off is slower execution and the need for each tool to be installed and on PATH.

**Contracts are separate JSON files, not inline assertions in test code.**
Why: Contracts need to be reviewable by non-developers (security leads, auditors). Keeping them in a declarative JSON format means they can be diffed, version-tracked, and validated independently of test logic. The cost is an extra layer of indirection when debugging a failure.

**Fixtures are checked into the repository, not generated on the fly.**
Why: Reproducibility. If a test fails, you need to know the exact input that caused it. Generated inputs introduce nondeterminism. The trade-off is repo size growth as fixtures accumulate, but for JSON/text fixtures this remains manageable.

**Single JSON Schema for all adapter outputs.**
Why: A shared schema forces structural consistency. Any consumer of benchmark results (dashboards, CI pipelines, audit logs) can parse output from any adapter without special-casing. This constrains what adapters can express but simplifies everything downstream.

**No runtime dependencies beyond the standard library.**
Why: The benchmark harness itself should be trivial to install and should never be the thing that breaks. Keeping it dependency-free (runtime) means it won't conflict with the tools it tests. Dev dependencies (pytest, ruff, numpy) are isolated to development and CI.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Test framework | pytest 8.2+ |
| Build system | setuptools 69+ with pyproject.toml |
| Linter | Ruff 0.8+ (E, F, I, W rules) |
| Dependency audit | pip-audit 2.7+ |
| Schema validation | JSON Schema (via `result.schema.json`) |
| CI/CD | GitHub Actions + Dependabot |
| Dashboard | Static HTML on GitHub Pages |

## Installation

```bash
# Clone the repository
git clone https://github.com/poojakira/mlsec-benchmark-suite.git
cd mlsec-benchmark-suite

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install in development mode with all dev dependencies
pip install -e ".[dev]"
```

Prerequisites:
- Python 3.10 or later
- The sibling tool repositories must be installed and accessible on PATH:
  - `aws-agent-identity-guard`
  - `hf-model-provenance-scanner`
  - `llm-redteam-framework` (classifier module)
  - `dataset-poisoning-detector`

## Quick Start

```bash
# Run the full regression suite
pytest tests/ -q

# Run only the IAM adapter tests
pytest tests/test_iam_lint_adapter.py -v

# Run via the CLI entrypoint
python -m mlsec_benchmark_suite run --suite smoke

# Generate a report
python -m mlsec_benchmark_suite report

# Validate results against schema
python -m mlsec_benchmark_suite validate
```

## Usage Examples

Run with timing to identify slow adapters:
```bash
pytest tests/ -v --durations=10
```

Run a single adapter's tests in isolation:
```bash
pytest tests/test_hf_scanner_adapter.py -v --tb=short
```

Use the installed CLI command directly:
```bash
mlsec-benchmark run --suite smoke
mlsec-benchmark report
mlsec-benchmark validate
```

---

## Security Considerations

**Fixture safety**: Test fixtures in `fixtures/` include intentionally malicious inputs (overly permissive IAM policies, prompt injection strings, poisoned dataset samples). These are inert data files, but be aware they exist when reviewing diffs or granting repository access.

**Tool execution**: Adapters shell out to external tool CLIs. If a tool under test is compromised or misconfigured, it will execute with the permissions of the user running the benchmark. Run benchmarks in isolated environments (containers, CI runners) rather than on production machines.

**No secrets in fixtures**: The IAM policy fixtures are synthetic. They do not reference real AWS accounts, ARNs, or credentials.

**Dependency management**: Dependabot is configured for automated security updates. The `pip-audit` dev dependency provides supply chain checks. The runtime has zero third-party dependencies, minimizing attack surface.

**Schema validation as a safety net**: Even if a tool produces unexpected output, the schema validation step will reject it before it's written to results, preventing malformed data from propagating to dashboards or audit logs.

---

## Evaluation Methods, Results, and Limitations

**How the suite evaluates tools:**
- Binary pass/fail against known-good and known-bad inputs
- Structural conformance of output to JSON Schema
- Contract adherence (expected findings count, expected verdict)
- Execution time monitoring (timeout detection)

**Current coverage:**

| Adapter | Fixtures | Test Functions |
|---------|----------|---------------|
| `iam_lint_adapter` | IAM policy JSON (valid + overprivileged) | Dedicated module |
| `hf_scanner_adapter` | HuggingFace model config files | Dedicated module |
| `prompt_injection_adapter` | Prompt strings (benign + malicious) | Dedicated module |
| `spectral_adapter` | Poisoned dataset samples | Dedicated module |
| Cross-adapter integration | All fixture types | `test_run_all.py` |
| CLI interface | Subcommand invocations | `test_cli.py` |

Total: 54 test functions across 7 test modules.

**Limitations:**
- The suite tests tools against static, curated fixtures. It does not measure real-world detection rates or false positive rates on production data.
- Adapters invoke tools via CLI, so any failure could be a tool bug or an environment issue (missing binary, wrong version). Error messages try to distinguish these but cannot always.
- Contract-based testing only catches regressions from previously defined behavior. Novel failure modes require new fixtures and updated contracts.
- No performance benchmarking beyond timeout detection. Execution time variability across environments means timing assertions would be flaky.

---

## Production Readiness Assessment

| Criterion | Status | Notes |
|-----------|--------|-------|
| Automated CI | Yes | GitHub Actions workflow + Dependabot |
| Test coverage | 29 functions, all 4 adapters exercised end-to-end | No coverage gaps in adapter layer |
| Schema validation | Enforced on every run | Catches output drift automatically |
| Contract versioning | `portfolio-smoke-v1.json` | Versioned filename allows schema evolution |
| Dependency hygiene | Zero runtime deps, pip-audit in CI | Minimal supply chain risk |
| Documentation | README, RUNBOOK, inline contracts | Operational playbook exists |
| Dashboard | GitHub Pages static site | At-a-glance visibility |
| Error handling | Skip semantics for missing tools | Graceful degradation when a tool is unavailable |

**What's missing for full production use:**
- No published releases or changelog (37 commits, no tags)
- No container image for hermetic execution
- No performance regression tracking over time
- Limited to 4 adapters; adding new tools requires manual adapter development

---

## Roadmap and Future Improvements

- **Container-based execution**: Package the suite and all tools into a Docker image so benchmarks run identically in any environment.
- **Performance tracking**: Store timing data per run and alert on regressions (e.g., adapter X suddenly takes 3x longer).
- **Adapter generator**: Scaffold new adapters from a template to reduce onboarding time for new tools.
- **Fuzzing mode**: Complement static fixtures with property-based testing to discover unexpected failure modes.
- **Result history and trending**: Persist results across runs for time-series analysis of pass rates and findings counts.
- **Broader fixture coverage**: Add edge cases (empty inputs, extremely large policies, unicode in prompts) to stress test adapter robustness.
- **Release automation**: Tag versions, publish to PyPI, maintain a changelog.

---

## References

- [RUNBOOK.md](https://github.com/poojakira/mlsec-benchmark-suite/blob/main/RUNBOOK.md) - Operational guide for running and extending benchmarks
- [JSON Schema Specification](https://json-schema.org/) - Foundation for output validation
- [pytest Documentation](https://docs.pytest.org/) - Test framework used by this suite
- [aws-agent-identity-guard](https://github.com/poojakira/aws-agent-identity-guard) - IAM policy linting tool tested by this suite
- [GitHub Pages Dashboard](https://poojakira.github.io/mlsec-benchmark-suite/) - Live status dashboard

---


## Additional Documentation

- [INCIDENT_RUNBOOK.md](INCIDENT_RUNBOOK.md) - benchmark infrastructure incident response
- [docs/CONTINUOUS_TRACKING.md](docs/CONTINUOUS_TRACKING.md) - how continuous trend tracking works
- [mlsec_benchmark_suite/tracker.py](mlsec_benchmark_suite/tracker.py) - trend analysis and regression detection

## License and Author

**License**: Apache-2.0

**Author**: Pooja Kiran

```
Copyright 2024 Pooja Kiran

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

---

## Engineering Lessons

The most useful testing infrastructure is the kind that tests the boundaries between systems, not just the systems themselves. Every tool in this portfolio had passing unit tests. What none of them had was a way to verify they still agreed on a shared contract. Building that verification layer took less code than any individual tool's test suite, but it caught more integration bugs than all of them combined. The key insight: treat tool output schemas the way you treat API contracts. Version them, validate them automatically, and break the build when they drift.
