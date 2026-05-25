"""Verify NetworkPolicies prevent agents from reaching the public internet.

The per-agent NetworkPolicy (Day 7 of Sprint 6) allows egress only to:
  - in-cluster services (Redis, Postgres, Jaeger, vector DBs)
  - kube-dns (UDP/TCP 53)
  - api.anthropic.com:443 (Orchestrator + Analyst only)

This test execs into a running echo-agent pod (which has no Anthropic
egress allowed) and tries to reach Cloudflare. It should time out.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

pytestmark = [pytest.mark.security]


def _find_running_pod(label: str, namespace: str = "synthetic-enterprise") -> str | None:
    result = subprocess.run(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            namespace,
            "-l",
            label,
            "--field-selector=status.phase=Running",
            "-o",
            "jsonpath={.items[0].metadata.name}",
            "--request-timeout=5s",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip()


def test_echo_agent_pod_cannot_reach_internet(require_cluster):
    pod = _find_running_pod("app=echo-agent")
    if pod is None:
        pytest.skip(
            "no running echo-agent pod found (deploy infrastructure/k3s/echo-agent.yaml first)"
        )

    # Use a 3s connect timeout — a working egress would resolve and connect well under that.
    result = subprocess.run(
        [
            "kubectl",
            "exec",
            "-n",
            "synthetic-enterprise",
            pod,
            "--",
            "sh",
            "-c",
            "timeout 4 wget -q --timeout=3 --tries=1 -O- https://1.1.1.1 2>&1; echo EXIT=$?",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    combined = (result.stdout + result.stderr).lower()
    # Acceptable evidence of denial: non-zero EXIT, "timed out", "unreachable",
    # or wget returning "no route to host".
    assert "exit=0" not in combined, (
        f"echo-agent pod successfully reached 1.1.1.1 — NetworkPolicy is NOT enforcing egress. "
        f"Output: {combined}"
    )
