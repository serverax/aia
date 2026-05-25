from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ClauseRationale(BaseModel):
    clause_id: str
    reasoning: str
    impact: str  # Positive/Negative impact on decision


class ExplanationPayload(BaseModel):
    matched_policies: List[str]
    rejected_policies: List[str]
    clause_rationale: List[ClauseRationale]
    decision_path: str
    triggering_evidence: List[str]
    metadata: Dict[str, Any] = {}


class ExplanationRequest(BaseModel):
    query: str
    decision_id: str
    context: Optional[str] = None
