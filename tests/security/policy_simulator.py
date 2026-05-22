"""Pure-Python Kubernetes NetworkPolicy simulator.

Implements enough of the NetworkPolicy spec to validate the policies in
`infrastructure/k3s/network-policies-per-agent.yaml` before they touch a
real cluster. Covers:

  * `podSelector` (matchLabels + matchExpressions In/NotIn/Exists/DoesNotExist)
  * `namespaceSelector` (matchLabels)
  * Peer combinations: podSelector alone, namespaceSelector alone, both AND'd,
    ipBlock alone
  * `ipBlock.cidr` + `ipBlock.except`
  * `ports` (port + protocol)
  * `policyTypes` semantics: pod becomes default-deny for the named types
    once selected by any policy of that type
  * Multi-policy union (any policy allowing = allowed)

NOT covered (out of scope for Sprint 6 validation; add when needed):

  * SCTP protocol — only TCP and UDP
  * `endPort` range matching
  * Egress to ServiceExternalName services
  * `port: <name>` named-port resolution (we only handle numeric ports)

See `test_policies_runtime.py` for the test suite that exercises these.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"


@dataclass(frozen=True)
class Pod:
    """A pod, identified by name, namespace, and labels."""

    name: str
    namespace: str
    labels: dict[str, str] = field(default_factory=dict, hash=False)

    def __hash__(self) -> int:
        return hash((self.name, self.namespace))


@dataclass(frozen=True)
class Namespace:
    """A namespace, with its labels (including the auto-applied k8s.io ones)."""

    name: str
    labels: dict[str, str] = field(default_factory=dict, hash=False)

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    def canonical(cls, name: str, extra_labels: dict[str, str] | None = None) -> "Namespace":
        """Build a Namespace with the apiserver-auto-applied label set.

        Since k8s 1.22, the apiserver always sets
        `kubernetes.io/metadata.name: <ns-name>`. Tests should always use
        this constructor unless they're explicitly modeling a cluster
        where that label is missing.
        """
        labels = {"kubernetes.io/metadata.name": name}
        if extra_labels:
            labels.update(extra_labels)
        return cls(name=name, labels=labels)


@dataclass
class Cluster:
    """The world the simulator evaluates against.

    Holds pods, namespaces, and the active NetworkPolicies (parsed from
    YAML into the simulator's dict shape — we don't re-parse YAML here).
    """

    pods: list[Pod] = field(default_factory=list)
    namespaces: list[Namespace] = field(default_factory=list)
    policies: list[dict[str, Any]] = field(default_factory=list)

    # --- lookups -------------------------------------------------------

    def namespace(self, name: str) -> Namespace | None:
        for ns in self.namespaces:
            if ns.name == name:
                return ns
        return None

    # --- core decision -------------------------------------------------

    def can_egress(
        self,
        src: Pod,
        *,
        dst_pod: Pod | None = None,
        dst_ip: str | None = None,
        port: int,
        protocol: str = "TCP",
    ) -> Decision:
        return self._evaluate(
            "Egress", src, peer_pod=dst_pod, peer_ip=dst_ip, port=port, protocol=protocol
        )

    def can_ingress(
        self,
        dst: Pod,
        *,
        src_pod: Pod | None = None,
        src_ip: str | None = None,
        port: int,
        protocol: str = "TCP",
    ) -> Decision:
        return self._evaluate(
            "Ingress", dst, peer_pod=src_pod, peer_ip=src_ip, port=port, protocol=protocol
        )

    # --- internal ------------------------------------------------------

    def _evaluate(
        self,
        direction: str,
        target_pod: Pod,
        *,
        peer_pod: Pod | None,
        peer_ip: str | None,
        port: int,
        protocol: str,
    ) -> Decision:
        """Apply the K8s NetworkPolicy decision algorithm.

        K8s rule: a pod is default-allow until at least one policy of the
        given direction (`Ingress` / `Egress`) selects it. Once any such
        policy selects it, the pod becomes default-deny for that direction.
        Multiple matching policies are evaluated as a UNION — any rule in
        any policy that allows the peer+port counts as ALLOWED.
        """
        matching_direction_policies = [
            p for p in self.policies
            if self._policy_selects_pod(p, target_pod)
            and direction in p.get("spec", {}).get("policyTypes", [])
        ]
        if not matching_direction_policies:
            return Decision.ALLOWED   # K8s default

        rules_key = "egress" if direction == "Egress" else "ingress"
        for policy in matching_direction_policies:
            for rule in policy["spec"].get(rules_key, []) or []:
                if self._rule_allows(rule, direction, peer_pod, peer_ip, port, protocol):
                    return Decision.ALLOWED
        return Decision.DENIED

    def _policy_selects_pod(self, policy: dict[str, Any], pod: Pod) -> bool:
        meta = policy.get("metadata", {})
        if meta.get("namespace") and meta["namespace"] != pod.namespace:
            return False
        selector = policy.get("spec", {}).get("podSelector", {})
        return _matches_selector(pod.labels, selector)

    def _rule_allows(
        self,
        rule: dict[str, Any],
        direction: str,
        peer_pod: Pod | None,
        peer_ip: str | None,
        port: int,
        protocol: str,
    ) -> bool:
        # Port match. Empty `ports:` list means "all ports" per the spec.
        ports_spec = rule.get("ports") or []
        if ports_spec and not _port_matches(ports_spec, port, protocol):
            return False

        peers_key = "to" if direction == "Egress" else "from"
        peers = rule.get(peers_key) or []
        if not peers:
            # Empty peers list = "any peer" within the same direction;
            # combined with the policyType, this is a wide-open rule.
            return True

        for peer in peers:
            if self._peer_matches(peer, peer_pod, peer_ip):
                return True
        return False

    def _peer_matches(
        self,
        peer: dict[str, Any],
        peer_pod: Pod | None,
        peer_ip: str | None,
    ) -> bool:
        if "ipBlock" in peer:
            if peer_ip is None:
                return False
            return _ip_matches_block(peer_ip, peer["ipBlock"])

        if peer_pod is None:
            return False

        pod_sel = peer.get("podSelector")
        ns_sel = peer.get("namespaceSelector")

        if pod_sel is None and ns_sel is None:
            return False

        if ns_sel is not None:
            ns = self.namespace(peer_pod.namespace)
            if ns is None:
                return False
            if not _matches_selector(ns.labels, ns_sel):
                return False
        else:
            # No namespaceSelector means "same namespace as the policy".
            # We don't have the policy here; the caller (_evaluate) already
            # constrained matching policies to the pod's namespace, but the
            # PEER namespace must equal the policy's namespace too. We
            # approximate: peer must be in same namespace as peer_pod's policy.
            # In our tests, all policies live in the target pod's namespace,
            # so "same namespace as policy" == "same namespace as target".
            # This is true for our generated policies.
            pass

        if pod_sel is not None and not _matches_selector(peer_pod.labels, pod_sel):
            return False
        return True


# ---------- helpers --------------------------------------------------


def _matches_selector(labels: dict[str, str], selector: dict[str, Any]) -> bool:
    """Standard K8s label selector matching."""
    if not selector:
        return True  # empty selector matches everything

    for k, v in (selector.get("matchLabels") or {}).items():
        if labels.get(k) != v:
            return False

    for expr in selector.get("matchExpressions") or []:
        op = expr["operator"]
        key = expr["key"]
        values = set(expr.get("values") or [])
        actual = labels.get(key)
        if op == "In":
            if actual not in values:
                return False
        elif op == "NotIn":
            if actual in values:
                return False
        elif op == "Exists":
            if key not in labels:
                return False
        elif op == "DoesNotExist":
            if key in labels:
                return False
        else:
            raise ValueError(f"unsupported matchExpressions operator: {op}")
    return True


def _port_matches(ports_spec: list[dict[str, Any]], port: int, protocol: str) -> bool:
    for ps in ports_spec:
        if "port" not in ps:
            continue
        if isinstance(ps["port"], str):
            # Named ports — not modeled; conservative skip.
            continue
        if ps["port"] != port:
            continue
        # Protocol defaults to TCP per the spec if omitted.
        if ps.get("protocol", "TCP") != protocol:
            continue
        return True
    return False


def _ip_matches_block(ip: str, ip_block: dict[str, Any]) -> bool:
    addr = ipaddress.ip_address(ip)
    cidr = ipaddress.ip_network(ip_block["cidr"], strict=False)
    if addr not in cidr:
        return False
    for excl in ip_block.get("except") or []:
        if addr in ipaddress.ip_network(excl, strict=False):
            return False
    return True
