import json
import os
from pathlib import Path

import pytest

from mlsec_benchmark_suite import cli

IDENTITY = {
    "repository": "poojakira/mlsec-benchmark-suite",
    "repository_commit": "0" * 40,
    "artifact_digest": "sha256:artifact",
    "model_hash": "sha256:model",
    "dependency_lock_hash": "sha256:lock",
    "created_at": "2026-07-29T00:00:00+00:00",
}


def run_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("MLSEC_BENCH_SIGNING_KEY", "test-signing-key")
    out = tmp_path / "smoke.json"
    cli.main(
        [
            "run-smoke",
            "--output",
            out.as_posix(),
            "--repository",
            IDENTITY["repository"],
            "--repository-commit",
            IDENTITY["repository_commit"],
            "--artifact-digest",
            IDENTITY["artifact_digest"],
            "--model-hash",
            IDENTITY["model_hash"],
            "--dependency-lock-hash",
            IDENTITY["dependency_lock_hash"],
            "--created-at",
            IDENTITY["created_at"],
        ]
    )
    return out


def test_smoke_result_covers_every_category_and_validates(tmp_path, monkeypatch):
    out = run_smoke(tmp_path, monkeypatch)
    result = json.loads(out.read_text(encoding="utf-8"))

    assert sorted(result["results"]) == sorted(cli.CATEGORIES)
    assert result["signature"]["algorithm"] == "hmac-sha256"
    cli.validate_result(result, require_signature=True)
    for field in cli.REQUIRED_IDENTITY_FIELDS:
        assert result["input_identity"][field]


def test_smoke_result_is_deterministic_for_fixed_inputs(tmp_path, monkeypatch):
    first = run_smoke(tmp_path / "one", monkeypatch)
    second = run_smoke(tmp_path / "two", monkeypatch)

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_missing_evidence_fails_validation(tmp_path, monkeypatch):
    out = run_smoke(tmp_path, monkeypatch)
    result = json.loads(out.read_text(encoding="utf-8"))
    del result["input_identity"]["model_hash"]

    with pytest.raises(ValueError, match="input_identity"):
        cli.validate_result(result)


def test_cli_refuses_to_overwrite_historical_results(tmp_path, monkeypatch):
    out = run_smoke(tmp_path, monkeypatch)
    before = out.read_text(encoding="utf-8")

    # main() now handles expected errors cleanly: it returns a non-zero exit
    # code and prints a readable message instead of raising a raw traceback.
    exit_code = cli.main(
        [
            "run-smoke",
            "--output",
            out.as_posix(),
            "--repository-commit",
            IDENTITY["repository_commit"],
            "--artifact-digest",
            IDENTITY["artifact_digest"],
            "--model-hash",
            IDENTITY["model_hash"],
            "--dependency-lock-hash",
            IDENTITY["dependency_lock_hash"],
            "--created-at",
            IDENTITY["created_at"],
        ]
    )
    assert exit_code == 2
    # The existing artifact must be left untouched.
    assert out.read_text(encoding="utf-8") == before


def test_report_is_generated_from_result_json(tmp_path, monkeypatch):
    out = run_smoke(tmp_path, monkeypatch)
    report = tmp_path / "report.md"
    cli.main(["report", out.as_posix(), "--output", report.as_posix()])

    text = report.read_text(encoding="utf-8")
    assert "ML Security Benchmark Report" in text
    assert IDENTITY["repository_commit"] in text
    for category in cli.CATEGORIES:
        assert category in text


def test_signature_detects_tampering(tmp_path, monkeypatch):
    out = run_smoke(tmp_path, monkeypatch)
    result = json.loads(out.read_text(encoding="utf-8"))
    result["input_identity"]["model_hash"] = "sha256:tampered"

    assert not cli.verify_signature(result, os.environ["MLSEC_BENCH_SIGNING_KEY"])
