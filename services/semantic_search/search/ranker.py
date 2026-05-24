from typing import List, Dict, Any
from ..vector_store.schemas import SearchResult


class Ranker:
    def __init__(self):
        pass

    def score_confidence(self, score: float, metric: str = "cosine") -> float:
        """Convert raw similarity score to a 0-1 confidence level."""
        if metric == "cosine":
            # For cosine, score is usually 0-1 already (Inner Product of normalized vectors)
            return max(0.0, min(float(score), 1.0))
        else:  # L2
            # For L2, lower is better. Convert distance to confidence.
            # This is a heuristic.
            return 1.0 / (1.0 + float(score))

    def rerank(self, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank results (placeholder for more complex logic)."""
        # Sort by score descending (higher is better for cosine)
        return sorted(results, key=lambda x: x.score, reverse=True)
