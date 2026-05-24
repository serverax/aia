import os
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import anthropic
from .citation_tracker import CitationTracker

from libs.communication.config import Config


class RAGSystem:
    def __init__(self, qdrant_host=Config.QDRANT_HOST, qdrant_port=Config.QDRANT_PORT):
        self.qdrant_client = QdrantClient(url=f"http://{qdrant_host}:{qdrant_port}")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.anthropic_client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.citation_tracker = CitationTracker()
        self.vector_size = 384

    def vectorize_query(self, query: str) -> List[float]:
        """Convert query to vector."""
        return self.model.encode(query).tolist()

    def search_qdrant(
        self, vector: List[float], collection_name="uk_compliance", limit=10
    ) -> List[Dict[str, Any]]:
        """Search Qdrant for relevant chunks."""
        results = self.qdrant_client.query(
            collection_name=collection_name, query_vector=vector, limit=limit
        )
        return [
            {
                "id": hit.payload.get("id") or str(hit.id),
                "text": hit.payload.get("text"),
                "regulation": hit.payload.get("regulation"),
                "section": hit.payload.get("section"),
                "source": hit.payload.get("source"),
                "score": hit.score,
            }
            for hit in results
        ]

    def rerank_results(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple reranking based on scores (placeholder for more complex reranker)."""
        # In a real system, use a cross-encoder or Cohere Rerank API
        return sorted(results, key=lambda x: x["score"], reverse=True)

    def assemble_context(self, results: List[Dict[str, Any]]) -> str:
        """Assemble context string for the LLM."""
        context_parts = []
        for doc in results:
            context_parts.append(f"Source ID: {doc['id']}\nContent: {doc['text']}")
        return "\n\n".join(context_parts)

    async def query(self, user_query: str, collection_name="uk_compliance") -> Dict[str, Any]:
        """Full RAG pipeline: Query -> Answer + Citations."""
        # 1. Vectorize
        vector = self.vectorize_query(user_query)

        # 2. Search
        retrieved_docs = self.search_qdrant(vector, collection_name=collection_name)

        # 3. Rerank
        reranked_docs = self.rerank_results(user_query, retrieved_docs)

        # 4. Assemble Context
        context = self.assemble_context(reranked_docs)

        # 5. Call LLM (Claude)
        prompt = f"""
        Use the following context to answer the user's question. 
        For every claim you make, you MUST cite the source using the format [CITATION: source_id].
        If you don't know the answer based on the context, say so.

        CONTEXT:
        {context}

        USER QUESTION:
        {user_query}

        ANSWER:
        """

        # In actual implementation, check if mock is needed
        if os.environ.get("ANTHROPIC_API_KEY") == "mock_key":
            # Mock response for testing
            if reranked_docs:
                doc = reranked_docs[0]
                answer_text = f"Based on {doc['regulation']}, {doc['text']} [CITATION: {doc['id']}]"
            else:
                answer_text = "I could not find relevant information in the provided context."
        else:
            message = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                temperature=0,
                system="You are a precise legal assistant. Always cite your sources.",
                messages=[{"role": "user", "content": prompt}],
            )
            answer_text = message.content[0].text

        # 6. Extract and Validate Citations
        citations = self.citation_tracker.extract_citations(answer_text)
        validation = self.citation_tracker.validate_citations(citations, reranked_docs)

        return {
            "answer": answer_text,
            "citations": citations,
            "validation": validation,
            "retrieved_docs": reranked_docs,
            "confidence_score": (
                max([doc["score"] for doc in reranked_docs]) if reranked_docs else 0.0
            ),
        }
