from typing import List, Dict, Any, Optional
from ..vector_store.faiss_store import FAISSStore
from ..embedding.embedder import Embedder
from .query_processor import QueryProcessor
from .ranker import Ranker
from ..vector_store.schemas import SearchResult


class SemanticSearchEngine:
    def __init__(self, vector_store: FAISSStore, embedder: Embedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.query_processor = QueryProcessor()
        self.ranker = Ranker()

    def search(
        self, query: str, top_k: int = 10, filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Perform end-to-end semantic search."""
        # 1. Process query
        normalized_query = self.query_processor.normalize(query)
        expanded_query = self.query_processor.expand_query(normalized_query)

        # 2. Embed query
        query_vector = self.embedder.embed(expanded_query)[0]

        # 3. Search vector store
        raw_results = self.vector_store.search(query_vector, top_k=top_k, filters=filters)

        # 4. Rerank and score
        reranked = self.ranker.rerank(raw_results)

        final_results = []
        for res in reranked:
            confidence = self.ranker.score_confidence(res.score, self.vector_store.metric)
            item = res.metadata.copy()
            item["id"] = res.id
            item["score"] = res.score
            item["confidence"] = confidence
            final_results.append(item)

        return final_results
