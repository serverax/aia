"""Hash-chain helpers for tamper-evident compliance audit records."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

GENESIS_HASH = "0" * 64


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_audit_hash(
    *,
    previous_hash: str | None,
    timestamp: datetime,
    agent_id: str,
    event_type: str,
    decision: str,
    reason: str,
    source: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """Build a deterministic SHA-256 hash for one audit event."""
    body = {
        "previous_hash": previous_hash or GENESIS_HASH,
        "timestamp": timestamp.astimezone(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "event_type": event_type,
        "decision": decision,
        "reason": reason,
        "source": source,
        "payload": payload or {},
    }
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditChainEntry:
    timestamp: datetime
    agent_id: str
    event_type: str
    decision: str
    reason: str
    source: str
    payload: dict[str, Any]
    previous_hash: str | None
    audit_hash: str


def verify_audit_chain(entries: list[AuditChainEntry]) -> tuple[bool, int | None]:
    """Verify an ordered audit chain.

    Returns ``(True, None)`` when valid, otherwise ``(False, index)`` for the
    first invalid row.
    """
    expected_previous = GENESIS_HASH
    for index, entry in enumerate(entries):
        if (entry.previous_hash or GENESIS_HASH) != expected_previous:
            return False, index
        expected_hash = build_audit_hash(
            previous_hash=entry.previous_hash,
            timestamp=entry.timestamp,
            agent_id=entry.agent_id,
            event_type=entry.event_type,
            decision=entry.decision,
            reason=entry.reason,
            source=entry.source,
            payload=entry.payload,
        )
        if entry.audit_hash != expected_hash:
            return False, index
        expected_previous = entry.audit_hash
    return True, None
