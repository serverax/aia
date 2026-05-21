"""Verify Kyverno's pod hardening policies block bad pod specs."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.security]


WRITABLE_ROOT_POD = """
apiVersion: v1
kind: Pod
metadata:
  name: writable-root-test
  labels:
    app: e2e-test
spec:
  restartPolicy: Never
  containers:
    - name: shell
      image: busybox:1.36
      command: ["sh", "-c", "sleep 1"]
      securityContext:
        readOnlyRootFilesystem: false   # <-- violates aia-readonly-root-fs
        allowPrivilegeEscalation: false
        runAsNonRoot: true
        capabilities:
          drop: ["ALL"]
"""

HOST_PATH_POD = """
apiVersion: v1
kind: Pod
metadata:
  name: hostpath-test
  labels:
    app: e2e-test
spec:
  restartPolicy: Never
  containers:
    - name: shell
      image: busybox:1.36
      command: ["sh", "-c", "sleep 1"]
      securityContext:
        readOnlyRootFilesystem: true
        allowPrivilegeEscalation: false
        runAsNonRoot: true
        capabilities:
          drop: ["ALL"]
      volumeMounts:
        - name: host-root
          mountPath: /host
  volumes:
    - name: host-root
      hostPath:
        path: /                  # <-- violates aia-no-host-mounts
"""

PRIVILEGED_POD = """
apiVersion: v1
kind: Pod
metadata:
  name: privileged-caps-test
  labels:
    app: e2e-test
spec:
  restartPolicy: Never
  containers:
    - name: shell
      image: busybox:1.36
      command: ["sh", "-c", "sleep 1"]
      securityContext:
        readOnlyRootFilesystem: true
        allowPrivilegeEscalation: true   # <-- violates aia-no-privilege-escalation
        runAsNonRoot: true
        capabilities:
          drop: ["ALL"]
"""


def _assert_denied(result, expected_policy: str):
    assert result.returncode != 0, (
        f"Expected Kyverno to reject the pod, but apply succeeded. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert "policy" in combined or "validation" in combined, (
        f"Rejection happened but not from a policy: {combined}"
    )
    assert expected_policy.lower() in combined, (
        f"Expected policy `{expected_policy}` to fire; got: {combined}"
    )


def test_writable_root_filesystem_rejected(require_kyverno_policies, kubectl_apply, kubectl_delete):
    kubectl_delete("pod", "writable-root-test")
    result = kubectl_apply(WRITABLE_ROOT_POD)
    _assert_denied(result, "aia-readonly-root-fs")


def test_host_path_volume_rejected(require_kyverno_policies, kubectl_apply, kubectl_delete):
    kubectl_delete("pod", "hostpath-test")
    result = kubectl_apply(HOST_PATH_POD)
    _assert_denied(result, "aia-no-host-mounts")


def test_privilege_escalation_rejected(require_kyverno_policies, kubectl_apply, kubectl_delete):
    kubectl_delete("pod", "privileged-caps-test")
    result = kubectl_apply(PRIVILEGED_POD)
    _assert_denied(result, "aia-no-privilege-escalation")
