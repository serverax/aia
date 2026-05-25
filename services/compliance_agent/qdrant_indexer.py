import hashlib

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class QdrantIndexer:
    def __init__(self, host="localhost", port=6333, model=None):
        self.client = QdrantClient(url=f"http://{host}:{port}")
        # Lazily load model unless injected (keeps tests fast/stable).
        self.model = model
        self.vector_size = 384  # Dimension for all-MiniLM-L6-v2

    def create_collection(self, collection_name="uk_compliance"):
        """Create UK compliance collection."""
        print(f"Creating collection: {collection_name}")
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )

    def embed_text(self, text):
        """Generate embedding for text."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = self.model.encode(text)
        return embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)

    @staticmethod
    def deterministic_point_id(source_id: str) -> str:
        """Build stable IDs without weak hashing algorithms."""
        return hashlib.sha256(source_id.encode("utf-8")).hexdigest()

    def index_legislation(self, collection_name="uk_compliance"):
        """Index sample UK legislation."""
        print(f"Indexing sample legislation into {collection_name}...")

        # Sample data based on Employment Rights Act 1996
        acts = [
            {
                "id": "era-1996-s1",
                "regulation": "Employment Rights Act 1996",
                "section": "Section 1",
                "text": "An employer shall give to an employee a written statement of particulars of employment.",
                "jurisdiction": "UK",
                "source": "https://www.legislation.gov.uk/ukpga/1996/23/section/1",
            },
            {
                "id": "era-1996-s13",
                "regulation": "Employment Rights Act 1996",
                "section": "Section 13",
                "text": "An employer shall not make a deduction from wages of a worker employed by him.",
                "jurisdiction": "UK",
                "source": "https://www.legislation.gov.uk/ukpga/1996/23/section/13",
            },
        ]

        points = []
        for act in acts:
            embedding = self.embed_text(act["text"])
            # Use a deterministic ID based on the act ID
            point_id = self.deterministic_point_id(act["id"])
            points.append(PointStruct(id=point_id, vector=embedding, payload=act))

        self.client.upsert(collection_name=collection_name, points=points)
        print(f"Successfully indexed {len(points)} points.")


if __name__ == "__main__":
    # For local testing, assume port-forward is active or running locally
    indexer = QdrantIndexer()
    indexer.create_collection()
    indexer.index_legislation()
