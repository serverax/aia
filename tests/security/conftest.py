"""Shared fixtures for Sprint 6 security E2E tests.

All tests in this directory require:
  1. `kubectl` available on PATH.
  2. KUBECONFIG pointing at the live Hetzner cluster.
  3. The Sprint 6 admission policies applied (sigstore + Kyverno).

If any precondition is missing, the test skips with a clear reason
rather than failing — this lets the offline test suite stay green
while Sprint 6 cluster install is still pending.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterator

import pytest


def _kubectl_available() -> bool:
    return shutil.which("kubectl") is not None


def _cluster_reachable() -> bool:
    try:
        result = subprocess.run(
            ["kubectl", "version", "--request-timeout=5s", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _policy_installed(kind: str, name: str) -> bool:
    try:
        result = subprocess.run(
            ["kubectl", "get", kind, name, "--request-timeout=5s"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(scope="session")
def require_cluster() -> None:
    if not _kubectl_available():
        pytest.skip("kubectl not on PATH")
    if not _cluster_reachable():
        pytest.skip("cluster not reachable (KUBECONFIG?)")


@pytest.fixture(scope="session")
def require_sigstore_policy(require_cluster) -> None:
    if not _policy_installed("clusterimagepolicy", "aia-images-must-be-signed"):
        pytest.skip(
            "ClusterImagePolicy `aia-images-must-be-signed` missing — "
            "apply infrastructure/security/cluster-image-policy.yaml first"
        )


@pytest.fixture(scope="session")
def require_kyverno_policies(require_cluster) -> None:
    for policy in ("aia-readonly-root-fs", "aia-drop-all-capabilities"):
        if not _policy_installed("clusterpolicy", policy):
            pytest.skip(
                f"Kyverno ClusterPolicy `{policy}` missing — "
                "apply infrastructure/security/kyverno-policies.yaml first"
            )


@pytest.fixture
def kubectl_apply():
    """Returns a callable that runs `kubectl apply -f -` with given YAML stdin.

    Returns the CompletedProcess so tests can inspect returncode + stderr.
    """
    def _apply(yaml_doc: str, *, namespace: str = "ordinox-ai"):
        return subprocess.run(
            ["kubectl", "apply", "-n", namespace, "-f", "-"],
            input=yaml_doc,
            capture_output=True,
            text=True,
            timeout=30,
        )
    return _apply


@pytest.fixture
def kubectl_delete():
    """Best-effort cleanup helper for tests that create resources."""
    created: list[tuple[str, str, str]] = []   # (kind, name, namespace)

    def _track(kind: str, name: str, namespace: str = "ordinox-ai"):
        created.append((kind, name, namespace))

    yield _track

    for kind, name, namespace in created:
        subprocess.run(
            ["kubectl", "delete", kind, name, "-n", namespace, "--ignore-not-found", "--wait=false"],
            capture_output=True,
            timeout=20,
        )


# Test namespace used for E2E manifests. Must already exist (created by Sprint 1).
TEST_NAMESPACE = os.environ.get("AIA_TEST_NAMESPACE", "ordinox-ai")
