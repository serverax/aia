from typing import Any, Dict, Optional

from libs.communication.config import Config
from services.rag_system.rag_system import RAGSystem

from .event_hub import notify_agent_step
from .recommendation_generator import RecommendationGenerator
from .risk_analyzer import RiskAnalyzer


class DomainAnalystAgent:
    def __init__(self, qdrant_host=Config.QDRANT_HOST, qdrant_port=Config.QDRANT_PORT):
        self.rag = RAGSystem(qdrant_host=qdrant_host, qdrant_port=qdrant_port)
        self.risk_analyzer = RiskAnalyzer()
        self.recommendation_generator = RecommendationGenerator()

    async def analyze(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive analysis pipeline.
        """
        await notify_agent_step("analyst", "planning", "started")

        # Step 1: Use RAG to get information
        await notify_agent_step("analyst", "retrieval", "in_progress", {"query": query})
        rag_result = await self.rag.query(query)
        analysis_text = rag_result["answer"]
        citations = rag_result["citations"]

        # Step 2: Assess risks
        await notify_agent_step("analyst", "risk_assessment", "in_progress")
        risk_assessment = self.risk_analyzer.assess(analysis_text, citations)

        # Step 3: Generate recommendations
        await notify_agent_step("analyst", "recommendations", "in_progress")
        recommendations = self.recommendation_generator.generate(analysis_text, risk_assessment)

        await notify_agent_step("analyst", "finalizing", "complete")

        return {
            "analysis": analysis_text,
            "citations": citations,
            "risk_assessment": risk_assessment,
            "recommendations": recommendations,
            "confidence": rag_result.get("confidence_score", 0.0),
        }
