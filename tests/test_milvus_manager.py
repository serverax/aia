import pytest
from unittest.mock import MagicMock, patch
from services.analyst_agent.milvus_manager import MilvusManager

@pytest.fixture
def manager():
    with patch('services.analyst_agent.milvus_manager.SentenceTransformer'):
        return MilvusManager()

def test_embed_text(manager):
    # Mock the transformer model's encode method
    manager.model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
    embedding = manager.embed_text("test")
    assert len(embedding) == 384
    assert embedding[0] == 0.1

@patch('services.analyst_agent.milvus_manager.Collection')
def test_create_client_collection(mock_collection, manager):
    client_id = "test_client"
    manager.create_client_collection(client_id)
    mock_collection.assert_called_once()
    assert f"client_{client_id}" in mock_collection.call_args[0]
