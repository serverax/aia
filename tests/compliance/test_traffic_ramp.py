from __future__ import annotations

import pytest

from scripts.compliance.blue_green_lib import (
    DeploymentState,
    EndpointState,
    PodState,
    kubectl_rollback_commands,
    kubectl_weight_command,
    next_weight_sequence,
    ratio_within_tolerance,
    rollback_required,
    rollout_gate_decision,
)


def ready_deployment() -> DeploymentState:
    return DeploymentState("compliance-service", desired=2, ready=2, available=2)


def ready_pods() -> list[PodState]:
    return [
        PodState("compliance-service-1", phase="Running", ready=True, restarts=0),
        PodState("compliance-service-2", phase="Running", ready=True, restarts=0),
    ]


def ready_endpoints() -> list[EndpointState]:
    return [EndpointState("compliance-service", addresses=2)]


def test_rollout_gate_ready_state_passes() -> None:
    ok, reasons = rollout_gate_decision(ready_deployment(), ready_pods(), ready_endpoints())
    assert ok
    assert reasons == []


def test_rollout_gate_blocks_partial_ready_deployment() -> None:
    ok, reasons = rollout_gate_decision(
        DeploymentState("compliance-service", desired=2, ready=1, available=1),
        ready_pods(),
        ready_endpoints(),
    )
    assert not ok
    assert "deployment ready 1/2" in reasons


def test_rollout_gate_blocks_pending_pod() -> None:
    ok, reasons = rollout_gate_decision(
        ready_deployment(),
        [PodState("compliance-service-1", phase="Pending", ready=False, restarts=0)],
        ready_endpoints(),
    )
    assert not ok
    assert "compliance-service-1 phase=Pending" in reasons


def test_rollout_gate_blocks_crash_loop() -> None:
    ok, reasons = rollout_gate_decision(
        ready_deployment(),
        [
            PodState(
                "compliance-service-1",
                phase="Running",
                ready=False,
                restarts=3,
                reason="CrashLoopBackOff",
            )
        ],
        ready_endpoints(),
    )
    assert not ok
    assert "compliance-service-1 blocked: CrashLoopBackOff" in reasons


def test_rollout_gate_blocks_missing_endpoint() -> None:
    ok, reasons = rollout_gate_decision(ready_deployment(), ready_pods(), [])
    assert not ok
    assert "compliance-service has no endpoints" in reasons


def test_rollout_gate_can_require_blue_and_green_endpoints_after_apply() -> None:
    ok, reasons = rollout_gate_decision(
        ready_deployment(),
        ready_pods(),
        [
            EndpointState("compliance-service-blue", addresses=2),
            EndpointState("compliance-service-green", addresses=2),
        ],
        require_services=("compliance-service-blue", "compliance-service-green"),
    )
    assert ok
    assert reasons == []


def test_apply_sequence_manifest_contains_five_documents() -> None:
    text = open("infrastructure/compliance/blue-green-traffic-split.yaml", encoding="utf-8").read()
    docs = [part for part in text.split("---") if part.strip()]
    assert len(docs) == 5


def test_apply_sequence_defines_blue_service() -> None:
    text = open("infrastructure/compliance/blue-green-traffic-split.yaml", encoding="utf-8").read()
    assert "name: compliance-service-blue" in text
    assert "color: blue" in text


def test_apply_sequence_defines_green_service() -> None:
    text = open("infrastructure/compliance/blue-green-traffic-split.yaml", encoding="utf-8").read()
    assert "name: compliance-service-green" in text
    assert "color: green" in text


def test_apply_sequence_defines_stable_ingress() -> None:
    text = open("infrastructure/compliance/blue-green-traffic-split.yaml", encoding="utf-8").read()
    assert "name: compliance-service-blue" in text
    assert "host: ordinoxai.com" in text
    assert "host: dev.ordinoxai.com" in text


def test_apply_sequence_defines_canary_ingress() -> None:
    text = open("infrastructure/compliance/blue-green-traffic-split.yaml", encoding="utf-8").read()
    assert "name: compliance-service-green-canary" in text
    assert 'nginx.ingress.kubernetes.io/canary: "true"' in text
    assert 'nginx.ingress.kubernetes.io/canary-weight: "5"' in text


def test_apply_sequence_defines_plan_configmap() -> None:
    text = open("infrastructure/compliance/blue-green-traffic-split.yaml", encoding="utf-8").read()
    assert "name: compliance-blue-green-plan" in text
    assert '"strategy": "nginx-ingress-canary"' in text


@pytest.mark.parametrize("weight", [0, 5, 25, 50, 100])
def test_traffic_weight_command_uses_expected_weight(weight: int) -> None:
    command = kubectl_weight_command("ordinox-ai", weight)
    assert command[-2] == f"nginx.ingress.kubernetes.io/canary-weight={weight}"


def test_traffic_weight_sequence_matches_sprint10_plan() -> None:
    assert next_weight_sequence() == [0, 5, 25, 50, 100]


def test_traffic_ratio_passes_within_two_percent() -> None:
    ok, observed = ratio_within_tolerance(25, blue_hits=76, green_hits=24)
    assert ok
    assert observed == 24


def test_traffic_ratio_fails_outside_two_percent() -> None:
    ok, observed = ratio_within_tolerance(50, blue_hits=60, green_hits=40)
    assert not ok
    assert observed == 40


def test_traffic_ratio_rejects_zero_requests() -> None:
    with pytest.raises(ValueError):
        ratio_within_tolerance(5, blue_hits=0, green_hits=0)


def test_rollback_required_for_high_latency() -> None:
    required, reasons = rollback_required(
        p95_ms=6000,
        error_rate_percent=0,
        critical_findings=0,
        high_findings=0,
        pod_restarts=0,
        endpoint_missing=False,
    )
    assert required
    assert "p95 latency above 5000ms" in reasons


def test_rollback_required_for_security_finding() -> None:
    required, reasons = rollback_required(
        p95_ms=100,
        error_rate_percent=0,
        critical_findings=1,
        high_findings=0,
        pod_restarts=0,
        endpoint_missing=False,
    )
    assert required
    assert "critical ZAP finding" in reasons


def test_rollback_not_required_for_clean_metrics() -> None:
    required, reasons = rollback_required(
        p95_ms=250,
        error_rate_percent=0.1,
        critical_findings=0,
        high_findings=0,
        pod_restarts=0,
        endpoint_missing=False,
    )
    assert not required
    assert reasons == []


def test_rollback_commands_include_weight_reset_and_undo() -> None:
    commands = kubectl_rollback_commands("ordinox-ai")
    flat = [" ".join(command) for command in commands]
    assert "nginx.ingress.kubernetes.io/canary-weight=0" in flat[0]
    assert "rollout undo deployment/compliance-service-green" in flat[1]
    assert "get endpoints compliance-service-blue compliance-service-green -o wide" in flat[2]
