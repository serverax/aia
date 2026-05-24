"""Unit tests for the Cosign-compatible verifier.

These don't need the cosign binary — we generate an ECDSA-P256 keypair
in-process, sign a blob, and verify. The math matches cosign's default
sign-blob format byte-for-byte.
"""

from __future__ import annotations

import pytest

from services.tool_sandbox.verifier import (
    CosignVerifier,
    SignatureVerificationError,
    generate_test_keypair,
    sign_blob_for_testing,
)

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module")
def keypair():
    return generate_test_keypair()


def test_verifies_a_valid_signature(keypair):
    private_pem, public_pem = keypair
    blob = b"hello world"
    sig = sign_blob_for_testing(blob, private_pem)
    verifier = CosignVerifier(public_pem)
    verifier.verify(blob, sig)  # no exception = pass


def test_rejects_tampered_blob(keypair):
    private_pem, public_pem = keypair
    blob = b"original bytes"
    sig = sign_blob_for_testing(blob, private_pem)
    verifier = CosignVerifier(public_pem)
    with pytest.raises(SignatureVerificationError, match="does not match"):
        verifier.verify(blob + b"!", sig)


def test_rejects_tampered_signature(keypair):
    private_pem, public_pem = keypair
    blob = b"some bytes"
    sig = sign_blob_for_testing(blob, private_pem)
    verifier = CosignVerifier(public_pem)
    # Flip the last base64 character (which round-trips through a valid base64
    # alphabet but produces a different signature).
    flipped = sig[:-1] + ("A" if sig[-1] != "A" else "B")
    with pytest.raises(SignatureVerificationError):
        verifier.verify(blob, flipped)


def test_rejects_signature_from_different_key(keypair):
    private_pem, public_pem = keypair
    blob = b"some bytes"
    sig = sign_blob_for_testing(blob, private_pem)
    # Different key entirely.
    _, other_pub = generate_test_keypair()
    verifier = CosignVerifier(other_pub)
    with pytest.raises(SignatureVerificationError):
        verifier.verify(blob, sig)


def test_rejects_non_base64_signature(keypair):
    _, public_pem = keypair
    verifier = CosignVerifier(public_pem)
    with pytest.raises(SignatureVerificationError, match="base64"):
        verifier.verify(b"blob", "not-base64-!!!")


def test_rejects_non_ecdsa_public_key():
    """RSA / Ed25519 keys should be rejected at construction.

    We don't want a misconfigured ConfigMap silently dropping us to a
    different algorithm. Cosign defaults to ECDSA-P256; anything else
    requires explicit verifier extension.
    """
    # Build an Ed25519 public key PEM the slow way (cryptography lib).
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    ed = ed25519.Ed25519PrivateKey.generate().public_key()
    ed_pem = ed.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with pytest.raises(ValueError, match="ECDSA"):
        CosignVerifier(ed_pem)
