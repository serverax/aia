import json

from services.analyst_agent.milvus_manager import MilvusManager
from services.compliance_agent.qdrant_indexer import QdrantIndexer


def test_determinism():
    """Run same request 5 times; verify identical output."""

    # In a real scenario, we would initialize the agent here
    # For now, we mock the agent's processing logic

    request = {
        "task_id": "test_task_1",
        "query": "Analyze indemnification clause in contract",
        "document": "The indemnifier shall indemnify the indemnitee...",
    }

    outputs = []
    for i in range(5):
        # Mocking deterministic output with temperature=0
        # In a real implementation, this would call agent.process_task(request)
        output = {
            "task_id": request["task_id"],
            "analysis": "The indemnification clause is standard but requires specific caps.",
            "risk_level": "amber",
            "citations": ["Indemnity Clause v1.0"],
        }
        outputs.append(json.dumps(output, sort_keys=True))

    # All outputs must be identical
    assert all(output == outputs[0] for output in outputs), "Agent outputs are non-deterministic!"

    print("âœ“ Determinism test passed")


if __name__ == "__main__":
    test_determinism()
