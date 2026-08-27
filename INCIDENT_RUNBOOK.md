# Incident Runbook — MLSec Benchmark Suite

This runbook covers common incidents related to the benchmark infrastructure, their diagnosis, and resolution procedures.

---

## Table of Contents

1. [Benchmark Run Failure](#1-benchmark-run-failure)
2. [Coverage Gate Failure](#2-coverage-gate-failure)
3. [Regression Alert Triggered](#3-regression-alert-triggered)
4. [Result File Corruption](#4-result-file-corruption)
5. [HMAC Signature Validation Failure](#5-hmac-signature-validation-failure)
6. [Adapter Connection Failure](#6-adapter-connection-failure)
7. [CI Pipeline Timeout](#7-ci-pipeline-timeout)
8. [Tracking Report Generation Failure](#8-tracking-report-generation-failure)

---

## 1. Benchmark Run Failure

### Symptoms
- CI `tracker` job fails at "Run benchmark suite" step
- Local `python -m mlsec_benchmark_suite.runner` exits with non-zero code

### Diagnosis
1. Check the error output for stack traces
2. Verify all adapters are properly configured:
   ```bash
   python -c "from mlsec_benchmark_suite import adapters; print(adapters.list_available())"
   ```
3. Check that model endpoints (if external) are reachable
4. Verify input data files exist and are not corrupted

### Resolution
- **Missing dependencies:** Run `pip install -e ".[dev]"` to reinstall
- **Adapter misconfiguration:** Check environment variables and adapter config in `config/`
- **External endpoint down:** Wait and retry; check provider status pages
- **Data corruption:** Restore from git history: `git checkout HEAD -- data/`

### Escalation
If unresolved after 15 minutes, notify the team lead in #mlsec-benchmarks Slack channel.

---

## 2. Coverage Gate Failure

### Symptoms
- CI `test` job fails with message: `FAIL Required test coverage of 85% not reached`
- `pytest --cov-fail-under=85` exits with non-zero code

### Diagnosis
1. Check coverage report for uncovered lines:
   ```bash
   pytest tests/ --cov=mlsec_benchmark_suite --cov-report=term-missing
   ```
2. Identify which files have low coverage
3. Check if new code was added without corresponding tests

### Resolution
- **New code without tests:** Write tests for uncovered paths
- **Removed tests:** Restore deleted tests or write replacements
- **Unreachable code:** Remove dead code or mark with `# pragma: no cover` (with justification)

### Prevention
- Always add tests in the same PR as new functionality
- Review coverage report before requesting review

---

## 3. Regression Alert Triggered

### Symptoms
- CI `tracker` job fails with: `❌ N regression(s) detected!`
- PR comment shows ⚠️ Regression Alerts table
- Metric degraded by more than 10% from baseline

### Diagnosis
1. Review the trend report to identify which metrics regressed
2. Check the PR diff for changes that could affect performance:
   - Algorithm changes
   - Data preprocessing modifications
   - Dependency version bumps
3. Run benchmarks locally to confirm:
   ```bash
   python -m mlsec_benchmark_suite.runner --output results/
   python -m mlsec_benchmark_suite.tracker results/
   ```

### Resolution
- **Legitimate regression:** Fix the code causing the degradation
- **Environmental noise:** Re-run benchmarks 3 times; if 2/3 pass, it's flaky
- **Expected regression (tradeoff):** Document the tradeoff in the PR description and update baseline:
  ```bash
  # After team approval, update the baseline
  python -m mlsec_benchmark_suite.tracker results/ --update-baseline
  ```
- **Incorrect baseline:** If the baseline itself was faulty, reset it with team consensus

### Escalation
If regression is confirmed and cannot be resolved in the current sprint, create a tracking issue and get tech lead approval to merge with known regression.

---

## 4. Result File Corruption

### Symptoms
- Tracker reports fewer results than expected
- JSON parse errors in tracker output
- Missing `metrics` key in result files

### Diagnosis
1. Validate result files:
   ```bash
   python -c "
   import json
   from pathlib import Path
   for f in Path('results').glob('*.json'):
       try:
           data = json.loads(f.read_text())
           assert 'metrics' in data, f'Missing metrics in {f}'
       except Exception as e:
           print(f'CORRUPT: {f} - {e}')
   "
   ```
2. Check git history for when corruption was introduced

### Resolution
- **Single file corrupt:** Restore from git: `git checkout HEAD~1 -- results/<file>`
- **Multiple files corrupt:** Investigate write process for bugs
- **Disk issues:** Check CI runner disk space and health

---

## 5. HMAC Signature Validation Failure

### Symptoms
- Result loading fails with signature validation error
- `InvalidSignatureError` in logs

### Diagnosis
1. Verify the HMAC signing key is correctly configured:
   ```bash
   echo $MLSEC_SIGNING_KEY | wc -c  # Should be non-empty
   ```
2. Check if result files were modified after signing
3. Verify the signing algorithm matches expectations

### Resolution
- **Key rotation needed:** Update `MLSEC_SIGNING_KEY` in CI secrets and re-sign existing results
- **Tampered results:** Investigate who/what modified the files; restore from signed backups
- **Algorithm mismatch:** Ensure all environments use the same HMAC algorithm (SHA-256)

### Escalation
Signature failures may indicate a security incident. Notify security team immediately if tampering is suspected.

---

## 6. Adapter Connection Failure

### Symptoms
- Benchmark hangs or times out on specific adapter
- `ConnectionError`, `TimeoutError`, or `AuthenticationError` in logs

### Diagnosis
1. Identify which adapter is failing from the error output
2. Test connectivity manually:
   ```bash
   python -c "
   from mlsec_benchmark_suite.adapters import get_adapter
   adapter = get_adapter('<adapter_name>')
   adapter.health_check()
   "
   ```
3. Check provider status pages for outages
4. Verify credentials are current and not expired

### Resolution
- **Network issue:** Check firewall rules, VPN connectivity
- **Expired credentials:** Rotate API keys/tokens in CI secrets
- **Provider outage:** Wait for resolution; skip adapter in CI with `--skip-adapter=<name>`
- **Rate limiting:** Add backoff/retry logic or reduce parallelism

---

## 7. CI Pipeline Timeout

### Symptoms
- GitHub Actions job exceeds the 60-minute timeout
- Job is killed mid-execution

### Diagnosis
1. Check which step consumed the most time
2. Look for infinite loops or hanging external calls
3. Check if dataset size increased significantly

### Resolution
- **Large dataset:** Implement sampling for CI runs: `--ci-mode` flag
- **Hanging adapter:** Add timeouts to adapter calls (default: 300s per benchmark)
- **Resource exhaustion:** Use a larger runner or optimize memory usage
- **Flaky external service:** Add circuit breaker pattern to adapters

### Configuration
Adjust timeout in `.github/workflows/ci.yml`:
```yaml
jobs:
  tracker:
    timeout-minutes: 45  # Adjust as needed
```

---

## 8. Tracking Report Generation Failure

### Symptoms
- `tracker.py` exits with unexpected error (not a regression alert)
- Report file is empty or malformed

### Diagnosis
1. Run tracker with verbose output:
   ```bash
   python -m mlsec_benchmark_suite.tracker results/ --verbose
   ```
2. Check if results directory has expected JSON structure
3. Verify Python dependencies are installed correctly

### Resolution
- **Import error:** Reinstall package: `pip install -e ".[dev]"`
- **Schema change:** If result format changed, update tracker to handle both old and new schemas
- **Permission error:** Check file system permissions on results/ and reports/ directories

---

## General Incident Guidelines

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| P1 - Critical | Benchmarks cannot run at all | < 1 hour | All adapters down, signing key compromised |
| P2 - High | Partial failure or data integrity issue | < 4 hours | Single adapter failure, result corruption |
| P3 - Medium | Degraded performance or flaky tests | < 1 business day | Intermittent timeouts, coverage drop |
| P4 - Low | Minor issues, no immediate impact | < 1 week | Report formatting issues, documentation gaps |

### Communication

1. Post in `#mlsec-benchmarks` Slack channel with:
   - Severity level
   - What's broken
   - Impact (who/what is affected)
   - Current status (investigating/mitigating/resolved)
2. For P1/P2: Page on-call via PagerDuty
3. Update status every 30 minutes for P1, every 2 hours for P2

### Post-Incident

After resolution:
1. Write a brief post-mortem (for P1/P2)
2. Create follow-up issues for preventive measures
3. Update this runbook if the incident revealed a gap

---

## Contacts

| Role | Contact | When |
|------|---------|------|
| Benchmark Team Lead | @team-lead | P1/P2 incidents |
| Security Team | @security | Signature/integrity incidents |
| Infrastructure | @infra | CI runner issues |
| On-Call | PagerDuty | After-hours P1 |
