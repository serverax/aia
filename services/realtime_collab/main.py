from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .manager import manager, websocket_operation_payload
from .models import ApplyOperationResponse, CollaborationOperation, DocumentSnapshot

app = FastAPI(title="Synthetic Enterprise Realtime Collaboration Service", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "realtime-collab"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/collab/documents/{document_id}", response_model=DocumentSnapshot)
async def get_document(document_id: str) -> DocumentSnapshot:
    return await manager.snapshot(document_id)


@app.post("/collab/documents/{document_id}/operations", response_model=ApplyOperationResponse)
async def apply_operation(
    document_id: str, operation: CollaborationOperation
) -> ApplyOperationResponse:
    return await manager.apply_operation(document_id, operation)


@app.websocket("/ws/collab/{document_id}")
async def collaboration_socket(websocket: WebSocket, document_id: str, client_id: str) -> None:
    await manager.connect(document_id, client_id, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            operation = websocket_operation_payload(payload, client_id=client_id)
            result = await manager.apply_operation(document_id, operation)
            if not result.accepted:
                await websocket.send_json(result.event.model_dump(mode="json"))
    except WebSocketDisconnect:
        await manager.disconnect(document_id, client_id)
