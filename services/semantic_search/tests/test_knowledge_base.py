import pytest
from services.semantic_search.knowledge_base.store_manager import KnowledgeBaseManager
from services.semantic_search.knowledge_base.sample_data import SAMPLE_DOCUMENTS
from services.semantic_search.vector_store.faiss_store import FAISSStore
from services.semantic_search.embedding.embedder import Embedder


@pytest.fixture
def kb_manager():
    store = FAISSStore(dimension=384, metric="cosine")
    # Mocking embedder to avoid loading model for simple KB tests if needed,
    # but let's use the real one since it's already tested.
    embedder = Embedder(cache_capacity=10)
    return KnowledgeBaseManager(store, embedder)


def test_add_sample_data(kb_manager):
    # Only add a few to keep it fast
    docs = SAMPLE_DOCUMENTS[:5]
    kb_manager.add_documents(docs)

    # Check if they were added to vector store
    # Search for something related to the first doc
    res = kb_manager.vector_store.search(kb_manager.embedder.embed(docs[0].content)[0], top_k=1)
    assert len(res) == 1
    assert res[0].metadata["title"] == docs[0].title


def test_document_listing(kb_manager):
    docs = SAMPLE_DOCUMENTS[:3]
    kb_manager.add_documents(docs)

    listed = kb_manager.list_documents()
    assert len(listed) == 3
    ids = {d.id for d in listed}
    assert "POL_001" in ids
