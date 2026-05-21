from typing import List, Union
from sentence_transformers import SentenceTransformer
from .cache_manager import EmbeddingCache

class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_capacity: int = 1000):
        self.model = SentenceTransformer(model_name)
        self.cache = EmbeddingCache(capacity=cache_capacity)
        self.dimension = 384 # Default for all-MiniLM-L6-v2

    def embed(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """Generate embeddings for a single string or a list of strings."""
        if isinstance(texts, str):
            texts = [texts]

        results = [None] * len(texts)
        to_embed = []
        to_embed_indices = []

        # Check cache first
        for i, text in enumerate(texts):
            cached = self.cache.get_embedding(text)
            if cached:
                results[i] = cached
            else:
                to_embed.append(text)
                to_embed_indices.append(i)

        # Batch embed missing texts
        if to_embed:
            embeddings = self.model.encode(to_embed).tolist()
            for i, emb in zip(to_embed_indices, embeddings):
                results[i] = emb
                self.cache.set_embedding(texts[i], emb)

        return results

    def get_stats(self):
        return self.cache.get_stats()
