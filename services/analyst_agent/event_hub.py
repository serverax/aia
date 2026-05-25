import asyncio
import json
from typing import Dict, List

from fastapi import WebSocket


class EventHub:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New HITL connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"HITL disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict):
        """Broadcast event to all connected HITL dashboards."""
        if not self.active_connections:
            return

        payload = json.dumps(message)
        # Create tasks for parallel broadcasting
        tasks = [connection.send_text(payload) for connection in self.active_connections]
        await asyncio.gather(*tasks, return_exceptions=True)


event_hub = EventHub()


async def notify_agent_step(agent_name: str, step: str, status: str, data: Dict = None):
    """Utility to broadcast agent progress."""
    await event_hub.broadcast(
        {
            "type": "agent_step",
            "agent": agent_name,
            "step": step,
            "status": status,
            "data": data or {},
        }
    )
