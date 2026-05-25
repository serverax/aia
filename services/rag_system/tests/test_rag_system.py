from unittest.mock import MagicMock, patch

import pytest

from services.rag_system.citation_tracker import CitationTracker
from services.rag_system.rag_system import RAGSystem


@pytest.fixture
def mock_qdrant():
    with patch("services.rag_system.rag_system.QdrantClient") as mock:
        yield mock


@pytest.fixture
def mock_transformer():
    with patch("services.rag_system.rag_system.SentenceTransformer") as mock:
        yield mock


@pytest.fixture
def mock_anthropic():
    with patch("services.rag_system.rag_system.anthropic.Anthropic") as mock:
        yield mock


@pytest.fixture
def rag_system(mock_qdrant, mock_transformer, mock_anthropic):
    return RAGSystem()


def test_vectorize_query(rag_system, mock_transformer):
    rag_system.model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
    vector = rag_system.vectorize_query("test query")
    assert len(vector) == 384
    assert vector[0] == 0.1


def test_citation_extraction():
    tracker = CitationTracker()
    text = "This is a claim [CITATION: doc_1] and another [CITATION: doc_2]."
    citations = tracker.extract_citations(text)
    assert citations == ["doc_1", "doc_2"]


def test_citation_validation():
    tracker = CitationTracker()
    retrieved_docs = [{"id": "doc_1"}, {"id": "doc_3"}]

    # Valid
    val1 = tracker.validate_citations(["doc_1"], retrieved_docs)
    assert val1["all_valid"] is True

    # Invalid
    val2 = tracker.validate_citations(["doc_2"], retrieved_docs)
    assert val2["all_valid"] is False
    assert val2["invalid"] == ["doc_2"]


@pytest.mark.asyncio
async def test_rag_query_pipeline(rag_system, mock_qdrant, mock_transformer, mock_anthropic):
    # Mock Qdrant query result
    mock_hit = MagicMock()
    mock_hit.payload = {
        "id": "doc_1",
        "text": "Employment Rights Act details.",
        "regulation": "ERA 1996",
    }
    mock_hit.score = 0.9
    # Use 'query' instead of 'search'
    rag_system.qdrant_client.query.return_value = [mock_hit]

    # Mock embedding
    rag_system.model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)

    # Mock Anthropic response
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="Based on ERA 1996, details. [CITATION: doc_1]")]
    rag_system.anthropic_client.messages.create.return_value = mock_msg

    # Run query
    result = await rag_system.query("What is the ERA?")

    assert "doc_1" in result["citations"]
    assert result["validation"]["all_valid"] is True
    assert result["confidence_score"] == 0.9
    assert "ERA 1996" in result["answer"]
