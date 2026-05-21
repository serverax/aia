from typing import List, Dict, Any
from .schemas import ComplianceDocument
from .processor import DocumentProcessor
from ..vector_store.faiss_store import FAISSStore
from ..vector_store.schemas import VectorItem
from ..embedding.embedder import Embedder

class KnowledgeBaseManager:
    def __init__(self, vector_store: FAISSStore, embedder: Embedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.processor = DocumentProcessor()
        self.documents: Dict[str, ComplianceDocument] = {}

    def add_documents(self, docs: List[ComplianceDocument]):
        """Process, embed, and add documents to the vector store."""
        all_chunks = []
        for doc in docs:
            # Store original document metadata
            self.documents[doc.id] = doc
            # Process and chunk
            chunks = self.processor.chunk_document(doc)
            all_chunks.extend(chunks)

        if not all_chunks:
            return

        # Batch embed all chunks
        texts = [chunk.content for chunk in all_chunks]
        embeddings = self.embedder.embed(texts)

        # Prepare vector items
        vector_items = []
        for chunk, embedding in zip(all_chunks, embeddings):
            metadata = chunk.model_dump()
            del metadata["content"] # Content is already in metadata? 
            # Actually, spec says schema has 'content'. 
            # I'll keep content in metadata for easy retrieval from FAISS store.
            metadata["content"] = chunk.content 
            
            vector_items.append(VectorItem(
                id=chunk.id,
                vector=embedding,
                metadata=metadata
            ))

        self.vector_store.add(vector_items)

    def get_document(self, doc_id: str) -> ComplianceDocument:
        """Retrieve original document by ID."""
        return self.documents.get(doc_id)

    def list_documents(self) -> List[ComplianceDocument]:
        """List all original documents."""
        return list(self.documents.values())
