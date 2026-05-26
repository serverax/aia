from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from .models import (
    ApplyOperationResponse,
    CollaborationEvent,
    CollaborationOperation,
    DocumentSnapshot,
    OperationType,
)


@dataclass
class DocumentSession:
    document_id: str
    content: str = ""
    version: int = 0
    clients: dict[str, WebSocket] = field(default_factory=dict)

    def snapshot(self) -> DocumentSnapshot:
        return DocumentSnapshot(
            document_id=self.document_id,
            version=self.version,
            content=self.content,
            active_clients=sorted(self.clients),
        )


class CollaborationManager:
    """In-memory deterministic collaboration manager.

    The manager rejects stale operations instead of attempting implicit merge.
    That keeps conflict resolution deterministic and auditable: clients must
    rebase on the current snapshot and resubmit.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, DocumentSession] = {}
        self._lock = asyncio.Lock()

    def _get_session(self, document_id: str) -> DocumentSession:
        if document_id not in self._sessions:
            self._sessions[document_id] = DocumentSession(document_id=document_id)
        return self._sessions[document_id]

    async def connect(
        self, document_id: str, client_id: str, websocket: WebSocket
    ) -> DocumentSnapshot:
        await websocket.accept()
        async with self._lock:
            session = self._get_session(document_id)
            session.clients[client_id] = websocket
            snapshot = session.snapshot()
        await websocket.send_json(
            CollaborationEvent(
                type="snapshot",
                document_id=document_id,
                version=snapshot.version,
                client_id=client_id,
                content=snapshot.content,
                active_clients=snapshot.active_clients,
            ).model_dump(mode="json")
        )
        await self.broadcast_presence(document_id)
        return snapshot

    async def disconnect(self, document_id: str, client_id: str) -> None:
        async with self._lock:
            session = self._sessions.get(document_id)
            if not session:
                return
            session.clients.pop(client_id, None)
        await self.broadcast_presence(document_id)

    async def snapshot(self, document_id: str) -> DocumentSnapshot:
        async with self._lock:
            return self._get_session(document_id).snapshot()

    async def reset(self) -> None:
        async with self._lock:
            self._sessions.clear()

    async def apply_operation(
        self, document_id: str, operation: CollaborationOperation
    ) -> ApplyOperationResponse:
        async with self._lock:
            session = self._get_session(document_id)

            if operation.base_version != session.version:
                event = CollaborationEvent(
                    type="conflict",
                    document_id=document_id,
                    version=session.version,
                    client_id=operation.client_id,
                    content=session.content,
                    operation=operation,
                    message=(
                        f"stale base_version {operation.base_version}; "
                        f"current version is {session.version}"
                    ),
                    active_clients=sorted(session.clients),
                )
                return ApplyOperationResponse(
                    accepted=False,
                    snapshot=session.snapshot(),
                    event=event,
                )

            try:
                session.content = self._apply_text_operation(session.content, operation)
            except ValueError as exc:
                event = CollaborationEvent(
                    type="error",
                    document_id=document_id,
                    version=session.version,
                    client_id=operation.client_id,
                    operation=operation,
                    message=str(exc),
                    active_clients=sorted(session.clients),
                )
                return ApplyOperationResponse(
                    accepted=False,
                    snapshot=session.snapshot(),
                    event=event,
                )

            session.version += 1
            snapshot = session.snapshot()
            event = CollaborationEvent(
                type="operation_applied",
                document_id=document_id,
                version=session.version,
                client_id=operation.client_id,
                content=session.content,
                operation=operation,
                active_clients=snapshot.active_clients,
            )

        await self.broadcast(document_id, event)
        return ApplyOperationResponse(accepted=True, snapshot=snapshot, event=event)

    async def broadcast_presence(self, document_id: str) -> None:
        snapshot = await self.snapshot(document_id)
        await self.broadcast(
            document_id,
            CollaborationEvent(
                type="presence",
                document_id=document_id,
                version=snapshot.version,
                active_clients=snapshot.active_clients,
            ),
        )

    async def broadcast(self, document_id: str, event: CollaborationEvent) -> None:
        async with self._lock:
            clients = list(self._get_session(document_id).clients.items())
        disconnected: list[str] = []
        for client_id, websocket in clients:
            try:
                await websocket.send_json(event.model_dump(mode="json"))
            except Exception:
                disconnected.append(client_id)
        if disconnected:
            async with self._lock:
                session = self._sessions.get(document_id)
                if session:
                    for client_id in disconnected:
                        session.clients.pop(client_id, None)

    @staticmethod
    def _apply_text_operation(content: str, operation: CollaborationOperation) -> str:
        if operation.operation == OperationType.replace:
            return operation.text
        if operation.position > len(content):
            raise ValueError("position exceeds document length")
        if operation.operation == OperationType.insert:
            return content[: operation.position] + operation.text + content[operation.position :]
        if operation.operation == OperationType.delete:
            end = operation.position + operation.length
            if end > len(content):
                raise ValueError("delete range exceeds document length")
            return content[: operation.position] + content[end:]
        raise ValueError(f"unsupported operation {operation.operation}")


manager = CollaborationManager()


def websocket_operation_payload(payload: dict[str, Any], client_id: str) -> CollaborationOperation:
    payload.setdefault("client_id", client_id)
    return CollaborationOperation.model_validate(payload)
