import json
from datetime import datetime
import uuid

def create_message(from_agent, to_agent, task_id, message_type, status, data=None):
    """Create a structured inter-agent message."""
    return {
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "from_agent": from_agent,
        "to_agent": to_agent,
        "task_id": task_id,
        "message_type": message_type,
        "status": status,
        "data": data or {},
        "metadata": {}
    }
