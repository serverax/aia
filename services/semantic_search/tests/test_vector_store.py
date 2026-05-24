import pytest
import numpy as np
import os
import shutil
from services.semantic_search.vector_store.faiss_store import FAISSStore
from services.semantic_search.vector_store.schemas import VectorItem


@pytest.fixture
def store():
    return FAISSStore(dimension=4, metric="cosine")


def test_add_search(store):
    items = [
        VectorItem(id="1", vector=[1.0, 0.0, 0.0, 0.0], metadata={"type": "policy"}),
        VectorItem(id="2", vector=[0.0, 1.0, 0.0, 0.0], metadata={"type": "guideline"}),
    ]
    store.add(items)

    # Search for something close to [1, 0, 0, 0]
    results = store.search([0.9, 0.1, 0.0, 0.0], top_k=1)
    assert len(results) == 1
    assert results[0].id == "1"
    assert results[0].metadata["type"] == "policy"


def test_metadata_filtering(store):
    items = [
        VectorItem(id="1", vector=[1.0, 0.0, 0.0, 0.0], metadata={"jurisdiction": "UK"}),
        VectorItem(id="2", vector=[0.9, 0.1, 0.0, 0.0], metadata={"jurisdiction": "US"}),
    ]
    store.add(items)

    # Search for [1, 0, 0, 0] but filter for US
    results = store.search([1.0, 0.0, 0.0, 0.0], top_k=1, filters={"jurisdiction": "US"})
    assert len(results) == 1
    assert results[0].id == "2"


def test_delete(store):
    items = [
        VectorItem(id="1", vector=[1.0, 0.0, 0.0, 0.0], metadata={}),
    ]
    store.add(items)
    assert len(store.search([1.0, 0.0, 0.0, 0.0], top_k=10)) == 1

    store.delete(["1"])
    assert len(store.search([1.0, 0.0, 0.0, 0.0], top_k=10)) == 0


def test_persistence(tmp_path):
    index_path = str(tmp_path / "faiss_index")
    store = FAISSStore(dimension=4, metric="cosine")
    items = [
        VectorItem(id="1", vector=[1.0, 0.0, 0.0, 0.0], metadata={"name": "test"}),
    ]
    store.add(items)
    store.save(index_path)

    new_store = FAISSStore(dimension=4, metric="cosine")
    new_store.load(index_path)

    results = new_store.search([1.0, 0.0, 0.0, 0.0], top_k=1)
    assert len(results) == 1
    assert results[0].id == "1"
    assert results[0].metadata["name"] == "test"
