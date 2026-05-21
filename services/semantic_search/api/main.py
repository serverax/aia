import os
from fastapi import FastAPI, Depends, HTTPException
from .schemas import SearchRequest, SearchResponseItem, EmbeddingRequest, EmbeddingResponse, DocumentCreateRequest
from ..vector_store.faiss_store import FAISSStore
from ..embedding.embedder import Embedder
from ..knowledge_base.store_manager import KnowledgeBaseManager
from ..search.semantic_search import SemanticSearchEngine
from ..knowledge_base.sample_data import SAMPLE_DOCUMENTS
from typing import List

app = FastAPI(title="Synthetic Enterprise Semantic Search Service")

# Dependency Injection / Global State
# In a real app, these would be initialized in a startup event or using a factory
dimension = 384
metric = "cosine"
store = FAISSStore(dimension=dimension, metric=metric)
embedder = Embedder()
kb_manager = KnowledgeBaseManager(store, embedder)
search_engine = SemanticSearchEngine(store, embedder)

# Bootstrap with sample data if index is empty
if not kb_manager.list_documents():
    kb_manager.add_documents(SAMPLE_DOCUMENTS)

@app.post("/search", response_model=List[SearchResponseItem])
async def search(request: SearchRequest):
    """Semantic search query."""
    try:
        results = search_engine.search(
            query=request.query, 
            top_k=request.top_k, 
            filters=request.filters
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed", response_model=EmbeddingResponse)
async def embed(request: EmbeddingRequest):
    """Generate embeddings for text."""
    try:
        embeddings = embedder.embed(request.texts)
        return {
            "embeddings": embeddings,
            "stats": embedder.get_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    """List all documents."""
    return kb_manager.list_documents()

@app.post("/documents")
async def add_documents(request: DocumentCreateRequest):
    """Add new documents to the knowledge base."""
    try:
        kb_manager.add_documents(request.documents)
        return {"status": "success", "count": len(request.documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Service health check."""
    return {
        "status": "healthy", 
        "vector_store": "FAISS", 
        "metric": metric,
        "embedding_model": "all-MiniLM-L6-v2",
        "document_count": len(kb_manager.list_documents())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
