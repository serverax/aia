import pytest
from unittest.mock import MagicMock
from services.compliance_agent.qdrant_indexer import QdrantIndexer

@pytest.fixture
def mock_qdrant():
    return MagicMock()

@pytest.fixture
def indexer(mock_qdrant):
    # Patch QdrantClient inside QdrantIndexer if needed, 
    # but for local testing we can just mock the client instance
    idx = QdrantIndexer()
    idx.client = mock_qdrant
    return idx

def test_embed_text(indexer):
    text = "Hello world"
    embedding = indexer.embed_text(text)
    assert isinstance(embedding, list)
    assert len(embedding) == 384

def test_index_legislation(indexer, mock_qdrant):
    indexer.index_legislation()
    # Verify recreate_collection or upsert was called
    assert mock_qdrant.upsert.called
    args, kwargs = mock_qdrant.upsert.call_args
    assert kwargs['collection_name'] == "uk_compliance"
    assert len(kwargs['points']) == 2
