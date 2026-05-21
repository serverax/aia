import pytest
from services.semantic_search.search.semantic_search import SemanticSearchEngine
from services.semantic_search.vector_store.faiss_store import FAISSStore
from services.semantic_search.embedding.embedder import Embedder
from services.semantic_search.knowledge_base.store_manager import KnowledgeBaseManager
from services.semantic_search.knowledge_base.sample_data import SAMPLE_DOCUMENTS

@pytest.fixture
def search_engine():
    store = FAISSStore(dimension=384, metric="cosine")
    embedder = Embedder(cache_capacity=50)
    kb_manager = KnowledgeBaseManager(store, embedder)
    kb_manager.add_documents(SAMPLE_DOCUMENTS[:10])
    return SemanticSearchEngine(store, embedder)

def test_semantic_search_basic(search_engine):
    # Search for data privacy (should find POL_001)
    results = search_engine.search("How do we handle personal data in the EU?", top_k=3)
    assert len(results) > 0
    assert results[0]["id"] == "POL_001"
    assert "GDPR" in results[0]["content"]

def test_semantic_search_filtering(search_engine):
    # Search for something general but filter by jurisdiction
    results = search_engine.search("policy", top_k=10, filters={"jurisdiction": "UK"})
    for res in results:
        assert res["jurisdiction"] == "UK"

def test_query_expansion(search_engine):
    # Search for '2fa' which is a synonym for 'mfa' in our processor
    # GUI_001 mentions MFA
    results = search_engine.search("2fa best practices", top_k=1)
    assert len(results) > 0
    assert "MFA" in results[0]["content"]
