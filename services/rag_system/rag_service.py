from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from .rag_system import RAGSystem

app = FastAPI(title="Synthetic Enterprise RAG Service")
rag_system = RAGSystem()


class QueryRequest(BaseModel):
    query: str
    collection: Optional[str] = "uk_compliance"


class QueryResponse(BaseModel):
    answer: str
    citations: List[str]
    validation: Dict[str, Any]
    confidence_score: float


class VerifyRequest(BaseModel):
    text: str
    retrieved_docs: List[Dict[str, Any]]


@app.post("/rag/query", response_model=QueryResponse)
async def perform_rag_query(request: QueryRequest = Body(...)):
    """Perform a RAG query and return answer with validated citations."""
    try:
        result = await rag_system.query(request.query, collection_name=request.collection)
        return QueryResponse(
            answer=result["answer"],
            citations=result["citations"],
            validation=result["validation"],
            confidence_score=result["confidence_score"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/status")
async def get_status():
    """Health check for the RAG service."""
    return {"status": "healthy", "service": "rag-system"}


@app.post("/rag/verify")
async def verify_citations(request: VerifyRequest = Body(...)):
    """Verify citations in a given text against a list of documents."""
    try:
        citations = rag_system.citation_tracker.extract_citations(request.text)
        validation = rag_system.citation_tracker.validate_citations(
            citations, request.retrieved_docs
        )
        return {"citations": citations, "validation": validation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
