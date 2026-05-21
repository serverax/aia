from pydantic import BaseModel, Field
from typing import Dict, Any

class ConfidenceFactors(BaseModel):
    data_completeness: float # 0.0-1.0
    policy_alignment: float   # 0.0-1.0
    evidence_quality: float   # 0.0-1.0

class ConfidenceScore(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    band: str # low|medium|high
    factors: ConfidenceFactors

def compute_confidence(data_completeness: float, policy_alignment: float, evidence_quality: float) -> ConfidenceScore:
    """
    Weighted confidence scoring logic.
    """
    # Simple weighted average for MVP
    # Data completeness (40%), Policy alignment (30%), Evidence quality (30%)
    score = (data_completeness * 0.4) + (policy_alignment * 0.3) + (evidence_quality * 0.3)
    score = round(score, 2)
    
    if score < 0.4:
        band = "low"
    elif score < 0.7:
        band = "medium"
    else:
        band = "high"
        
    return ConfidenceScore(
        score=score,
        band=band,
        factors=ConfidenceFactors(
            data_completeness=data_completeness,
            policy_alignment=policy_alignment,
            evidence_quality=evidence_quality
        )
    )
