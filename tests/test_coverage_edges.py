from __future__ import annotations

import runpy
import sys
from dataclasses import dataclass, field

import numpy as np
import pytest

from mlsec_benchmark_suite.adapters import hf_scanner_adapter as hf
from mlsec_benchmark_suite.adapters import iam_lint_adapter as iam
from mlsec_benchmark_suite.adapters import prompt_injection_adapter as prompt
from mlsec_benchmark_suite.adapters import spectral_adapter as spectral


@dataclass
class _Severity:
    value: str


@dataclass
class _Finding:
    rule_id: str = "HF999"
    severity: _Severity = field(default_factory=lambda: _Severity("high"))
    message: str = "test"
    evidence: str = "evidence"
    line_number: int = 7
    cwe: str = "CWE-20"


def test_module_entrypoint_help(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mlsec-benchmark", "--help"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module(
            "mlsec_benchmark_suite.__main__",
            run_name="mlsec_benchmark_suite._coverage_entrypoint",
        )
    assert exc.value.code == 0


def test_hf_finding_dataclass_serialization():
    out = hf._finding_to_dict(_Finding())
    assert out == {
        "rule": "HF999",
        "severity": "high",
        "message": "test",
        "evidence": "evidence",
        "line": 7,
        "cwe": "CWE-20",
    }


def test_hf_evaluate_false_negative_and_false_positive(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture.json"
    fixture.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(hf, "analyze_config_file", lambda *_args, **_kwargs: [])
    fn = hf._evaluate_fixture("bad.json", fixture, {"expected_findings": 1, "label": "known-bad"})
    assert fn["metrics"] == {"tp": 0, "fp": 0, "fn": 1}

    monkeypatch.setattr(
        hf,
        "analyze_config_file",
        lambda *_args, **_kwargs: [{"rule": "HF001", "severity": "high"}],
    )
    fp = hf._evaluate_fixture(
        "clean.json", fixture, {"expected_findings": 0, "label": "known-good"}
    )
    assert fp["metrics"] == {"tp": 0, "fp": 1, "fn": 0}


def test_hf_missing_dependency(monkeypatch):
    monkeypatch.setattr(hf, "analyze_config_file", None)
    with pytest.raises(ImportError, match="not installed"):
        hf.run_benchmark()


def test_hf_missing_fixture_and_checksum_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(hf, "analyze_config_file", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(hf, "DATASET_MANIFEST", tmp_path / "missing-manifest.json")
    with pytest.raises(FileNotFoundError, match="Missing fixture"):
        hf.run_benchmark(fixtures_dir=tmp_path)

    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    for name in hf.GROUND_TRUTH:
        (fixture_dir / name).write_text("{}", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"files":{"clean_bert_config.json":"sha256:not-the-real-digest"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(hf, "DATASET_MANIFEST", manifest)
    with pytest.raises(ValueError, match="checksum mismatch"):
        hf.run_benchmark(fixtures_dir=fixture_dir)


def test_iam_missing_dependency_and_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(iam, "ag", None)
    with pytest.raises(RuntimeError, match="required"):
        iam.run_benchmark()

    class _AG:
        @staticmethod
        def scan_policy_document(_policy):
            return []

    monkeypatch.setattr(iam, "ag", _AG)
    with pytest.raises(FileNotFoundError, match="Missing fixture"):
        iam.run_benchmark(fixtures_dir=tmp_path)


def test_prompt_injection_missing_dependency(monkeypatch):
    monkeypatch.setattr(prompt, "detect_injection", None)
    with pytest.raises(ImportError, match="not installed"):
        prompt.run_benchmark()


def test_spectral_missing_dependencies(monkeypatch):
    monkeypatch.setattr(spectral, "spectral_detect", None)
    with pytest.raises(ImportError, match="not installed"):
        spectral.run_benchmark()

    monkeypatch.setattr(spectral, "spectral_detect", lambda **_kwargs: [])
    monkeypatch.setattr(spectral, "np", None)
    with pytest.raises(ImportError, match="numpy"):
        spectral.run_benchmark()


def test_spectral_accepts_iterable_detector_output(monkeypatch):
    monkeypatch.setattr(spectral, "spectral_detect", lambda **_kwargs: [0, 1, 2])
    result = spectral.run_benchmark(
        {
            "n_samples": 20,
            "n_features": 3,
            "n_clusters": 2,
            "poison_rate": 0.0,
            "random_seed": 7,
            "cluster_separation": 2.0,
        }
    )
    metrics = result["results"]["spectral"]["aggregate_metrics"]
    assert metrics["total_detected"] == 3
    assert metrics["total_poisoned"] == 0
    assert metrics["detection_rate"] == 0.0


def test_synthetic_generator_shapes():
    data = spectral._generate_synthetic_data(
        n_samples=9,
        n_features=4,
        poison_rate=0.22,
        random_seed=3,
    )
    assert data["features"].shape == (9, 4)
    assert data["labels"].shape == (9,)
    assert data["poisoned_labels"].shape == (9,)
    assert data["poison_mask"].dtype == np.bool_
    assert data["n_poison"] == int(9 * 0.22)
