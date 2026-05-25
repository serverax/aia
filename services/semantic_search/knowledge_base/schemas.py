from typing import Any, Dict

from pydantic import BaseModel, Field


class ComplianceDocument(BaseModel):
    id: str
    type: str = Field(..., pattern="^(policy|guideline|case)$")
    title: str
    content: str
    jurisdiction: str = Field(..., pattern="^(US|EU|UK|GLOBAL)$")
    risk_category: str
    date: str  # YYYY-MM-DD
    source: str
    metadata: Dict[str, Any] = {}
