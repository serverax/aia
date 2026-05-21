import pytest
from services.semantic_search.embedding.embedder import Embedder

@pytest.fixture
def embedder():
    return Embedder(cache_capacity=5)

def test_embed_single(embedder):
    res = embedder.embed("hello world")
    assert len(res) == 1
    assert len(res[0]) == 384

def test_embed_batch(embedder):
    texts = ["apple", "banana", "cherry"]
    res = embedder.embed(texts)
    assert len(res) == 3
    for emb in res:
        assert len(emb) == 384

def test_caching(embedder):
    text = "cache me"
    # First call - miss
    embedder.embed(text)
    stats = embedder.get_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0
    
    # Second call - hit
    embedder.embed(text)
    stats = embedder.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1

def test_lru_eviction(embedder):
    # Cache capacity is 5
    for i in range(6):
        embedder.embed(f"text_{i}")
    
    # text_0 should be evicted
    stats = embedder.get_stats()
    initial_hits = stats["hits"]
    
    embedder.embed("text_0")
    stats = embedder.get_stats()
    assert stats["misses"] > 6 # Should be another miss
