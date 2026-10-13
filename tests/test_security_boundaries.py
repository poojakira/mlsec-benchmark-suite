import os

import pytest

from mlsec_benchmark_suite.cli import generate_ed25519_keypair, verify_dataset_checksums


def test_manifest_rejects_path_escape(tmp_path):
    with pytest.raises(ValueError, match="inside"):
        verify_dataset_checksums({"files": {"../outside": "sha256:any"}}, tmp_path)


def test_manifest_rejects_symlink_escape(tmp_path):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("private")
    (fixtures / "linked").symlink_to(outside)
    with pytest.raises(ValueError, match="inside"):
        verify_dataset_checksums({"files": {"linked": "sha256:any"}}, fixtures)


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits are not enforced on Windows")
def test_private_key_permissions(tmp_path):
    private = tmp_path / "private.pem"
    generate_ed25519_keypair(private, tmp_path / "public.pem")
    assert os.stat(private).st_mode & 0o777 == 0o600


def test_hmac_verification_rejects_unknown_algorithm():
    from mlsec_benchmark_suite.cli import sign_payload, verify_signature

    payload = {"result": "example"}
    payload["signature"] = sign_payload(payload, "test-key")
    assert verify_signature(payload, "test-key")
    payload["signature"]["algorithm"] = "unsupported"
    assert not verify_signature(payload, "test-key")
    payload["signature"]["algorithm"] = "hmac-sha256"
    payload["signature"]["value"] = None
    assert not verify_signature(payload, "test-key")


def test_hmac_verification_rejects_malformed_signature_shapes():
    from mlsec_benchmark_suite.cli import sign_payload, verify_signature

    for invalid in (None, [], "string"):
        assert not verify_signature({"signature": invalid}, "test-key")
    payload = {"result": "example"}
    payload["signature"] = sign_payload(payload, "test-key")
    payload["signature"]["value"] = "é" * 64
    assert not verify_signature(payload, "test-key")
