"""Verify sigstore/policy-controller rejects unsigned images in the namespace."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.security]


UNSIGNED_POD = """
apiVersion: v1
kind: Pod
metadata:
  name: unsigned-image-test
  labels:
    app: e2e-test
spec:
  restartPolicy: Never
  containers:
    - name: nginx
      image: nginx:latest    # Public image with no cosign signature against our key
      command: ["sh", "-c", "sleep 1"]
"""


def test_unsigned_image_is_rejected(require_sigstore_policy, kubectl_apply, kubectl_delete):
    kubectl_delete("pod", "unsigned-image-test")
    result = kubectl_apply(UNSIGNED_POD)
    assert result.returncode != 0, (
        f"Expected admission to reject unsigned image, but kubectl apply succeeded. "
        f"stdout: {result.stdout!r} stderr: {result.stderr!r}"
    )
    combined = (result.stdout + result.stderr).lower()
    # sigstore policy-controller's denial message varies by version; check
    # for any of the recognizable substrings.
    assert any(needle in combined for needle in (
        "no signatures found",
        "signature",
        "policy-controller",
        "no matching signatures",
        "denied",
    )), f"Unexpected rejection reason: {combined}"
