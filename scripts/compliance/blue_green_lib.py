from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class DeploymentState:
    name: str
    desired: int
    ready: int
    available: int


@dataclass(frozen=True)
class PodState:
    name: str
    phase: str
    ready: bool
    restarts: int
    reason: str = ""


@dataclass(frozen=True)
class EndpointState:
    service: str
    addresses: int


BLOCKED_REASONS = {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerError"}


def rollout_gate_decision(
    deployment: DeploymentState,
    pods: Sequence[PodState],
    endpoints: Sequence[EndpointState],
    require_services: Iterable[str] = ("compliance-service",),
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if deployment.ready < deployment.desired:
        reasons.append(f"deployment ready {deployment.ready}/{deployment.desired}")
    if deployment.available < deployment.desired:
        reasons.append(f"deployment available {deployment.available}/{deployment.desired}")

    if not pods:
        reasons.append("no pods found")
    for pod in pods:
        if pod.phase != "Running":
            reasons.append(f"{pod.name} phase={pod.phase}")
        if not pod.ready:
            reasons.append(f"{pod.name} not ready")
        if pod.reason in BLOCKED_REASONS:
            reasons.append(f"{pod.name} blocked: {pod.reason}")

    endpoint_map = {endpoint.service: endpoint.addresses for endpoint in endpoints}
    for service in require_services:
        if endpoint_map.get(service, 0) <= 0:
            reasons.append(f"{service} has no endpoints")

    return not reasons, reasons


def observed_green_percent(blue_hits: int, green_hits: int) -> float:
    total = blue_hits + green_hits
    if total <= 0:
        raise ValueError("traffic sample has zero requests")
    return (green_hits / total) * 100.0


def ratio_within_tolerance(
    target_green_percent: float,
    blue_hits: int,
    green_hits: int,
    tolerance_percent: float = 2.0,
) -> tuple[bool, float]:
    observed = observed_green_percent(blue_hits, green_hits)
    return abs(observed - target_green_percent) <= tolerance_percent, observed


def next_weight_sequence() -> list[int]:
    return [0, 5, 25, 50, 100]


def rollback_required(
    *,
    p95_ms: float,
    error_rate_percent: float,
    critical_findings: int,
    high_findings: int,
    pod_restarts: int,
    endpoint_missing: bool,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if endpoint_missing:
        reasons.append("green endpoint missing")
    if p95_ms > 5000:
        reasons.append("p95 latency above 5000ms")
    if error_rate_percent > 10:
        reasons.append("error rate above 10%")
    if critical_findings > 0:
        reasons.append("critical ZAP finding")
    if high_findings > 0:
        reasons.append("high ZAP finding")
    if pod_restarts > 0:
        reasons.append("pod restart detected")
    return bool(reasons), reasons


def kubectl_weight_command(namespace: str, weight: int) -> list[str]:
    if weight < 0 or weight > 100:
        raise ValueError("weight must be between 0 and 100")
    return [
        "kubectl",
        "-n",
        namespace,
        "annotate",
        "ingress",
        "compliance-service-green-canary",
        f"nginx.ingress.kubernetes.io/canary-weight={weight}",
        "--overwrite",
    ]


def kubectl_rollback_commands(namespace: str = "ordinox-ai") -> list[list[str]]:
    return [
        kubectl_weight_command(namespace, 0),
        ["kubectl", "-n", namespace, "rollout", "undo", "deployment/compliance-service-green"],
        [
            "kubectl",
            "-n",
            namespace,
            "get",
            "endpoints",
            "compliance-service-blue",
            "compliance-service-green",
            "-o",
            "wide",
        ],
    ]
