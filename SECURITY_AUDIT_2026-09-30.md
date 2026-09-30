# Security review, 30 September 2026

Reviewed baseline: `03850b7261f8e68531f68e038931e120a7b543f0`. Source review and focused regression verification; this is not proof that all vulnerabilities are absent.

## Fixes and reviewed controls

Manifest file paths are resolved and constrained to the fixture directory, rejecting traversal and escaping symlinks. Generated private Ed25519 keys are mode 0600 and created with exclusive/no-follow flags where supported.

## Verification

72 passed; one optional HF adapter test skipped. Tests ran in an isolated Python 3.12 environment. FastAPI TestClient required execution outside the default sandbox; a minimal unchanged app reproduced the sandbox deadlock. Final installed-environment pip-audit reported no known vulnerabilities. This does not cover every optional dependency, every container image, or arbitrary older environments allowed by broad dependency bounds.

## Secret history review

206 history matches were previously committed virtual-environment vendor tests/license metadata. Historical PEM files were certifi public CA bundles, not private keys. No tracked environment secret file was found. Gitleaks classifications are pattern matches, not provider validity checks. No provider key was tested or revoked, and fetched Git refs do not include every cached/forked copy. `.env` and local credential patterns remain ignored; example files must contain placeholders only.

## Deployment and remaining limits

This is a local CLI, not a network API: authentication, endpoint rate limits and remote uploads are not applicable. Embedded-key signature verification proves self-consistency; pass a trusted external public key for signer identity. Local input files and output paths are operator-controlled; do not expose this CLI to untrusted remote users without a separate authorization and sandbox boundary.
