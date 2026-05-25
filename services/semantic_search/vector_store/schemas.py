from typing import Any, Dict, List

from pydantic import BaseModel


class VectorItem(BaseModel):
    id: str
    vector: List[float]
    metadata: Dict[str, Any]


class SearchResult(BaseModel):
    id: str
    score: float
    metadata: Dict[str, Any]
