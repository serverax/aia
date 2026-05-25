"""Cosign signature verification — pure Python, no cosign binary needed.

`cosign sign-blob` produces a base64-encoded ECDSA-P256-SHA256 signature
over the blob's bytes. The matching public key is PEM-encoded. This
module verifies that pairing using `cryptography` directly, so the
verify path has no subprocess dependency.

The cosign CLI is still required at *signing* time (because it talks to
Vault to fetch the key); but at runtime — when an agent loads a `.wasm`
into the sandbox — we just need the math.

Production setup:
    pubkey_pem = load from cosign-system/aia-cosign-pubkey ConfigMap
    verifier = CosignVerifier(pubkey_pem)
    verifier.verify(wasm_bytes, sig_b64)   # raises on failure
"""

from __future__ import annotations

import base64
import logging
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey

logger = logging.getLogger(__name__)


class SignatureVerificationError(Exception):
    """Raised when a blob's signature does not validate against the key.

    Distinct from generic `InvalidSignature` so callers can log the
    tool name + key fingerprint with the failure.
    """


class SignatureVerifier(Protocol):
    """Minimum surface the tool registry depends on."""

    def verify(self, blob: bytes, signature_b64: str) -> None:
        """Raise `SignatureVerificationError` on failure; return None on success."""
        ...


class CosignVerifier:
    """Verifies signatures produced by `cosign sign-blob` with an ECDSA key."""

    def __init__(self, public_key_pem: bytes) -> None:
        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, EllipticCurvePublicKey):
            raise ValueError(
                f"Expected an ECDSA public key (P-256); got {type(key).__name__}. "
                "Cosign defaults to P-256; if you've configured an RSA or Ed25519 key, "
                "extend CosignVerifier accordingly."
            )
        self._key = key

    def verify(self, blob: bytes, signature_b64: str) -> None:
        try:
            signature_der = base64.b64decode(signature_b64, validate=True)
        except (ValueError, TypeError) as exc:
            raise SignatureVerificationError(f"signature is not valid base64: {exc}") from exc

        try:
            self._key.verify(signature_der, blob, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature as exc:
            raise SignatureVerificationError("signature does not match blob") from exc


class AllowAllVerifier:
    """Test-only stand-in. NEVER use in production.

    Imported by integration tests that want to bypass signing while still
    exercising the registry's verify→execute pipeline.
    """

    def verify(self, blob: bytes, signature_b64: str) -> None:  # noqa: D401
        return None


def generate_test_keypair() -> tuple[bytes, bytes]:
    """Create a fresh ECDSA-P256 keypair for tests.

    Returns (private_key_pem, public_key_pem).
    """
    private = ec.generate_private_key(ec.SECP256R1())
    public = private.public_key()
    return (
        private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
    )


def sign_blob_for_testing(blob: bytes, private_key_pem: bytes) -> str:
    """Produce a cosign-compatible base64 ECDSA-P256-SHA256 signature.

    Lives here (not in tests/) so other test modules in the repo can
    use it as a fixture helper. NOT for production signing — production
    signing always goes through `cosign sign-blob --key vault://...`.
    """
    key = serialization.load_pem_private_key(private_key_pem, password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise ValueError("expected ECDSA private key")
    signature_der = key.sign(blob, ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(signature_der).decode("ascii")
