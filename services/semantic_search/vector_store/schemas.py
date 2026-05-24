from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class VectorItem(BaseModel):
    id: str
    vector: List[float]
    metadata: Dict[str, Any]


class SearchResult(BaseModel):
    id: str
    score: float
    metadata: Dict[str, Any]
