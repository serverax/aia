import os
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .analyst_agent import DomainAnalystAgent
from .confidence import ConfidenceScore, compute_confidence
from .event_hub import event_hub
from .models.explanation import ClauseRationale, ExplanationPayload, ExplanationRequest
from .risk_analyzer import RiskAnalyzer

app = FastAPI(title="Synthetic Enterprise Analyst Service")


@app.websocket("/ws/hitl")
async def websocket_endpoint(websocket: WebSocket):
    await event_hub.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
            # Handle incoming HITL commands if needed
    except WebSocketDisconnect:
        event_hub.disconnect(websocket)


analyst_agent = DomainAnalystAgent()
risk_analyzer = RiskAnalyzer()


class AnalysisRequest(BaseModel):
    query: str
    context: Optional[str] = None


class AnalysisResponse(BaseModel):
    analysis: str
    citations: List[str]
    risk_assessment: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    confidence: float
    confidence_details: Optional[ConfidenceScore] = None


class RiskRequest(BaseModel):
    text: str
    citations: Optional[List[str]] = []


class ApprovalWorkflowPayload(BaseModel):
    request_type: str = Field(..., description="policy_change|document_release|exception")
    title: str
    description: str
    requestor: str
    deadline: str
    approval_strategy: str = "all_must_approve"
    metadata: Dict[str, Any] = {}


class ApprovalResponse(BaseModel):
    request_id: str
    risk_score: float
    sla_hours_recommended: int
    recommended_reviewers: List[str]
    analyst_summary: str
    confidence_details: Optional[ConfidenceScore] = None


@app.post("/analyst/approval/evaluate", response_model=ApprovalResponse)
async def evaluate_approval_payload(payload: ApprovalWorkflowPayload = Body(...)):
    """
    Evaluate an approval request payload and return analyst recommendation context.
    """
    valid_types = {"policy_change", "document_release", "exception"}
    valid_strategies = {"all_must_approve", "any_can_approve", "weighted_voting"}

    if payload.request_type not in valid_types:
        raise HTTPException(
            status_code=400, detail=f"Unsupported request_type: {payload.request_type}"
        )
    if payload.approval_strategy not in valid_strategies:
        raise HTTPException(
            status_code=400, detail=f"Unsupported approval_strategy: {payload.approval_strategy}"
        )

    try:
        risk_score = float(payload.metadata.get("risk_score", 5.0))
        recommended_reviewers = ["you@synthetic.io", "compliance_officer@synthetic.io"]
        if risk_score >= 8:
            recommended_reviewers.append("security_lead@synthetic.io")

        # Compute confidence score
        conf_details = compute_confidence(
            data_completeness=0.95 if payload.description else 0.5,
            policy_alignment=0.8,
            evidence_quality=0.85,
        )

        return ApprovalResponse(
            request_id=f"APR-EVAL-{payload.title[:8].upper()}",
            risk_score=risk_score,
            sla_hours_recommended=24 if risk_score >= 7 else 48,
            recommended_reviewers=recommended_reviewers,
            analyst_summary=(
                f"Approval '{payload.title}' requires "
                f"{len(recommended_reviewers)} reviewers based on risk score {risk_score}."
            ),
            confidence_details=conf_details,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyst/analyze", response_model=AnalysisResponse)
async def analyze_task(request: AnalysisRequest = Body(...)):
    """
    Main analysis endpoint.
    """
    try:
        result = await analyst_agent.analyze(request.query, request.context)

        # Inject multi-factor confidence scoring
        conf_details = compute_confidence(
            data_completeness=0.9,
            policy_alignment=0.85,
            evidence_quality=result.get("confidence", 0.8),
        )

        result["confidence_details"] = conf_details
        return AnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyst/risks-only")
async def assess_risks(request: RiskRequest = Body(...)):
    """Risk assessment only (without full analysis)."""
    try:
        risk_assessment = risk_analyzer.assess(request.text, request.citations)
        return {"risk_assessment": risk_assessment}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyst/decision/explain", response_model=ExplanationPayload)
async def explain_decision(request: ExplanationRequest = Body(...)):
    """
    Provide deep rationale for a specific decision.
    """
    # Mocked logic for MVP
    return ExplanationPayload(
        matched_policies=["POL_001", "POL_002"],
        rejected_policies=["POL_003"],
        clause_rationale=[
            ClauseRationale(
                clause_id="GDPR_Art_32",
                reasoning="Encryption protocols verified.",
                impact="Positive",
            ),
            ClauseRationale(
                clause_id="AML_KYC_Check",
                reasoning="Identity verification pending.",
                impact="Negative",
            ),
        ],
        decision_path="RAG retrieval -> Semantic policy mapping -> Keyword risk scoring",
        triggering_evidence=["Cleartext PII detected in log dump"],
        metadata={"decision_id": request.decision_id},
    )


@app.get("/analyst/status")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "analyst-agent"}


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("ANALYST_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("ANALYST_PORT", "8001"))
    uvicorn.run(app, host=host, port=port)
