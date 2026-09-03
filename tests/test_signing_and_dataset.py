"""Tests for Ed25519 public-key signing, dataset checksum verification, and
the --overwrite warning added to close issue #1.

These exercise the REAL cryptography-backed signing path (no mocks): a keypair
is generated, a result is signed, and the signature is verified with the public
key alone. Tamper detection is also asserted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlsec_benchmark_suite import cli

REPO_ROOT = Path(__file__).resolve().parent.parent
HF_FIXTURES = REPO_ROOT / "fixtures" / "hf_configs"
HF_MANIFEST = REPO_ROOT / "datasets" / "hf-scanner-fixtures.json"


def _minimal_result() -> dict:
    return {
        "schema_version": "1.0.0",
        "suite_version": "0.1.0",
        "created_at": "2026-09-03T00:00:00+00:00",
        "run_id": "deadbeefdeadbeef",
        "contract_version": "hf-scanner-v1",
        "results": {"hf_scanner": {"aggregate_metrics": {"precision": 1.0}}},
        "signature": {"algorithm": "unsigned", "payload_sha256": "", "value": ""},
    }


def test_ed25519_keygen_sign_verify_roundtrip(tmp_path: Path):
    priv = tmp_path / "signing_key.pem"
    pub = tmp_path / "signing_key.pub.pem"
    cli.generate_ed25519_keypair(priv, pub)
    assert priv.exists() and pub.exists()

    payload = _minimal_result()
    payload["signature"] = cli.sign_payload_ed25519(payload, priv)
    assert payload["signature"]["algorithm"] == "ed25519"
    assert payload["signature"]["value"]
    assert "BEGIN PUBLIC KEY" in payload["signature"]["public_key_pem"]

    # Verify with the standalone public key file...
    assert cli.verify_signature_ed25519(payload, pub) is True
    # ...and with the embedded public key (no external file needed).
    assert cli.verify_signature_ed25519(payload, None) is True


def test_ed25519_detects_tamper(tmp_path: Path):
    priv = tmp_path / "k.pem"
    pub = tmp_path / "k.pub.pem"
    cli.generate_ed25519_keypair(priv, pub)
    payload = _minimal_result()
    payload["signature"] = cli.sign_payload_ed25519(payload, priv)

    # Tamper with a signed field: verification must fail (digest mismatch).
    payload["results"]["hf_scanner"]["aggregate_metrics"]["precision"] = 0.5
    assert cli.verify_signature_ed25519(payload, pub) is False


def test_ed25519_wrong_key_fails(tmp_path: Path):
    priv1 = tmp_path / "a.pem"
    pub1 = tmp_path / "a.pub.pem"
    priv2 = tmp_path / "b.pem"
    pub2 = tmp_path / "b.pub.pem"
    cli.generate_ed25519_keypair(priv1, pub1)
    cli.generate_ed25519_keypair(priv2, pub2)
    payload = _minimal_result()
    payload["signature"] = cli.sign_payload_ed25519(payload, priv1)
    # Verifying with a different public key must fail.
    assert cli.verify_signature_ed25519(payload, pub2) is False


def test_sign_and_verify_cli(tmp_path: Path):
    priv = tmp_path / "k.pem"
    pub = tmp_path / "k.pub.pem"
    assert cli.main(["keygen-ed25519", "--private-out", str(priv), "--public-out", str(pub)]) == 0

    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(_minimal_result()), encoding="utf-8")
    signed_path = tmp_path / "signed.json"

    assert (
        cli.main(
            ["sign", str(result_path), "--private-key", str(priv), "--output", str(signed_path)]
        )
        == 0
    )
    # Verify via embedded key and via explicit public key.
    assert cli.main(["verify", str(signed_path)]) == 0
    assert cli.main(["verify", str(signed_path), "--public-key", str(pub)]) == 0


def test_verify_unsigned_returns_2(tmp_path: Path):
    result_path = tmp_path / "u.json"
    result_path.write_text(json.dumps(_minimal_result()), encoding="utf-8")
    assert cli.main(["verify", str(result_path)]) == 2


def test_verify_dataset_matches_committed_checksums():
    manifest = json.loads(HF_MANIFEST.read_text(encoding="utf-8"))
    # Should not raise: committed fixtures match committed checksums.
    cli.verify_dataset_checksums(manifest, HF_FIXTURES)


def test_verify_dataset_detects_mismatch(tmp_path: Path):
    manifest = {"files": {"x.json": "sha256:" + "0" * 64}}
    (tmp_path / "x.json").write_text("different content", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum verification failed"):
        cli.verify_dataset_checksums(manifest, tmp_path)


def test_verify_dataset_cli(tmp_path: Path):
    assert (
        cli.main(
            ["verify-dataset", "--manifest", str(HF_MANIFEST), "--fixtures-dir", str(HF_FIXTURES)]
        )
        == 0
    )


def test_overwrite_emits_warning(tmp_path: Path, capsys):
    target = tmp_path / "artifact.json"
    cli.write_json(target, {"a": 1})
    # Second write with overwrite=True must warn on stderr.
    cli.write_json(target, {"a": 2}, overwrite=True)
    captured = capsys.readouterr()
    assert "WARNING: --overwrite is replacing existing evidence artifact" in captured.err


def test_overwrite_refused_without_flag(tmp_path: Path):
    target = tmp_path / "artifact.json"
    cli.write_json(target, {"a": 1})
    with pytest.raises(FileExistsError):
        cli.write_json(target, {"a": 2})
