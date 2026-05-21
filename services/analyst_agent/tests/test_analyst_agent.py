import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from services.analyst_agent.analyst_agent import DomainAnalystAgent
from services.analyst_agent.risk_analyzer import RiskAnalyzer
from services.analyst_agent.recommendation_generator import RecommendationGenerator

@pytest.fixture
def mock_rag():
    with patch('services.analyst_agent.analyst_agent.RAGSystem') as mock:
        yield mock

@pytest.fixture
def agent(mock_rag):
    return DomainAnalystAgent()

@pytest.mark.asyncio
async def test_analyst_analyze(agent, mock_rag):
    """Test full analysis pipeline."""
    # Mock RAG result using AsyncMock for awaitable method
    mock_rag_instance = agent.rag
    mock_rag_instance.query = AsyncMock(return_value={
        "answer": "There is a potential fraud, loss, debt, bankruptcy and leverage risk which is a legal violation and breach of contract, resulting in downtime and gdpr issues.",
        "citations": ["doc_1"],
        "confidence_score": 0.85
    })
    
    result = await agent.analyze("Test query")
    
    assert "analysis" in result
    assert "citations" in result
    assert "risk_assessment" in result
    assert "recommendations" in result
    assert result["confidence"] == 0.85
    assert result["risk_assessment"]["overall_level"] in ["MEDIUM", "HIGH"]

def test_risk_assessment():
    """Test risk analyzer."""
    analyzer = RiskAnalyzer()
    # "fraud" (financial), "violation" (legal), "downtime" (operational)
    result = analyzer.assess("fraud loss bankruptcy violation downtime gdpr", [])
    
    assert result["overall_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert 0 <= result["overall_score"] <= 1
    assert result["factors"]["financial"] > 0
    assert result["factors"]["legal"] > 0
    assert result["factors"]["operational"] > 0
    assert result["factors"]["compliance"] > 0

def test_recommendations():
    """Test recommendation generation."""
    gen = RecommendationGenerator()
    risk_assessment = {
        "overall_level": "HIGH",
        "factors": {"compliance": 0.8, "financial": 0.1}
    }
    recommendations = gen.generate("analysis text", risk_assessment)
    
    assert len(recommendations) > 0
    assert all("priority" in r for r in recommendations)
    assert all("text" in r for r in recommendations)
    assert recommendations[0]["text"] == "Initiate immediate compliance audit for regulatory alignment."
