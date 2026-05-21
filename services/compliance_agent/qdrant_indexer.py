from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import requests
from sentence_transformers import SentenceTransformer
import hashlib

class QdrantIndexer:
    def __init__(self, host="localhost", port=6333):
        self.client = QdrantClient(url=f"http://{host}:{port}")
        # Using a local model for embeddings
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.vector_size = 384 # Dimension for all-MiniLM-L6-v2

    def create_collection(self, collection_name="uk_compliance"):
        """Create UK compliance collection."""
        print(f"Creating collection: {collection_name}")
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )

    def embed_text(self, text):
        """Generate embedding for text."""
        return self.model.encode(text).tolist()

    def index_legislation(self, collection_name="uk_compliance"):
        """Index sample UK legislation."""
        print(f"Indexing sample legislation into {collection_name}...")
        
        # Sample data based on Employment Rights Act 1996
        acts = [
            {
                'id': 'era-1996-s1',
                'regulation': 'Employment Rights Act 1996',
                'section': 'Section 1',
                'text': 'An employer shall give to an employee a written statement of particulars of employment.',
                'jurisdiction': 'UK',
                'source': 'https://www.legislation.gov.uk/ukpga/1996/23/section/1'
            },
            {
                'id': 'era-1996-s13',
                'regulation': 'Employment Rights Act 1996',
                'section': 'Section 13',
                'text': 'An employer shall not make a deduction from wages of a worker employed by him.',
                'jurisdiction': 'UK',
                'source': 'https://www.legislation.gov.uk/ukpga/1996/23/section/13'
            }
        ]
        
        points = []
        for act in acts:
            embedding = self.embed_text(act['text'])
            # Use a deterministic ID based on the act ID
            point_id = hashlib.md5(act['id'].encode()).hexdigest()
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload=act
            ))
        
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        print(f"Successfully indexed {len(points)} points.")

if __name__ == "__main__":
    # For local testing, assume port-forward is active or running locally
    indexer = QdrantIndexer()
    indexer.create_collection()
    indexer.index_legislation()
