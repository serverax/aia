from pymilvus import Collection, connections, CollectionSchema, FieldSchema, DataType
from sentence_transformers import SentenceTransformer
import time


class MilvusManager:
    def __init__(self, host="localhost", port="19530"):
        self.host = host
        self.port = port
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.vector_size = 384

    def connect(self):
        """Connect to Milvus server."""
        print(f"Connecting to Milvus at {self.host}:{self.port}")
        # In a real environment, this would connect to the Milvus server
        # For local testing, we might need a mock or a local Milvus instance
        try:
            connections.connect("default", host=self.host, port=self.port)
        except Exception as e:
            print(f"Failed to connect to Milvus: {e}")

    def create_client_collection(self, client_id: str):
        """Create isolated collection for client data."""
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.vector_size),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="document_type", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="created_at", dtype=DataType.INT64),
        ]
        schema = CollectionSchema(fields, f"Client {client_id} data")
        collection = Collection(f"client_{client_id}", schema)

        # Create partition for additional isolation if needed
        collection.create_partition(f"{client_id}_partition")
        return collection

    def embed_text(self, text):
        """Generate embedding for text."""
        return self.model.encode(text).tolist()

    def insert_document(self, client_id: str, doc_id: str, text: str, doc_type: str):
        """Insert client document with embedding."""
        collection = Collection(f"client_{client_id}")
        embedding = self.embed_text(text)

        entities = [[doc_id], [embedding], [text], [doc_type], [int(time.time() * 1000)]]

        collection.insert(entities, partition_name=f"{client_id}_partition")
        collection.flush()
        print(f"Inserted document {doc_id} into client_{client_id}")


if __name__ == "__main__":
    manager = MilvusManager()
    # manager.connect() # Skip connection for local run without server
