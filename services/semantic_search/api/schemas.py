from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ..knowledge_base.schemas import ComplianceDocument


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10
    filters: Optional[Dict[str, Any]] = None


class SearchResponseItem(BaseModel):
    id: str
    type: str
    title: str
    content: str
    jurisdiction: str
    risk_category: str
    score: float
    confidence: float
    metadata: Dict[str, Any]


class EmbeddingRequest(BaseModel):
    texts: List[str]


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    stats: Dict[str, Any]


class DocumentCreateRequest(BaseModel):
    documents: List[ComplianceDocument]
