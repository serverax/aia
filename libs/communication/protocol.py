import uuid
from datetime import UTC, datetime


def create_message(from_agent, to_agent, task_id, message_type, status, data=None):
    """Create a structured inter-agent message."""
    return {
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "task_id": task_id,
        "message_type": message_type,
        "status": status,
        "data": data or {},
        "metadata": {},
    }
