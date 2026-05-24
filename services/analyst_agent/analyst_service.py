from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import asyncio
import time

from .analyst_agent import DomainAnalystAgent
from .risk_analyzer import RiskAnalyzer
from .models.explanation import ExplanationPayload, ExplanationRequest, ClauseRationale
from .confidence import ConfidenceScore, compute_confidence
from .editor_agent import EditorAgent
from .models.finalizer import (
    FinalizeRequest,
    FinalizeResponse,
    DocumentDraft,
    FinalDocument,
    BulkExportRequest,
    BulkExportResponse,
)

app = FastAPI(title="Synthetic Enterprise Analyst Service")
analyst_agent = DomainAnalystAgent()
risk_analyzer = RiskAnalyzer()
editor_agent = EditorAgent()

# Job status store
export_jobs: Dict[str, Dict[str, Any]] = {}


# --- Previous Models ---
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


# --- HITL ---
from .event_hub import event_hub
from fastapi import WebSocket, WebSocketDisconnect


@app.websocket("/ws/hitl")
async def websocket_endpoint(websocket: WebSocket):
    await event_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_hub.disconnect(websocket)


# --- Endpoints ---


@app.post("/analyst/analyze", response_model=AnalysisResponse)
async def analyze_task(request: AnalysisRequest = Body(...)):
    try:
        result = await analyst_agent.analyze(request.query, request.context)
        conf_details = compute_confidence(0.9, 0.85, result.get("confidence", 0.8))
        result["confidence_details"] = conf_details
        editor_agent.create_draft(
            project_id=request.query[:10], agent_id="analyst-v1", content=result["analysis"]
        )
        return AnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyst/approval/evaluate", response_model=ApprovalResponse)
async def evaluate_approval_payload(payload: ApprovalWorkflowPayload = Body(...)):
    risk_score = float(payload.metadata.get("risk_score", 5.0))
    conf_details = compute_confidence(0.95 if payload.description else 0.5, 0.8, 0.85)
    return ApprovalResponse(
        request_id=f"APR-EVAL-{payload.title[:8].upper()}",
        risk_score=risk_score,
        sla_hours_recommended=24 if risk_score >= 7 else 48,
        recommended_reviewers=["you@synthetic.io", "compliance_officer@synthetic.io"],
        analyst_summary=f"Approval '{payload.title}' evaluated.",
        confidence_details=conf_details,
    )


@app.get("/analyst/document/preview")
async def preview_document(project_id: str, version: Optional[int] = None):
    html = editor_agent.get_preview(project_id, version)
    return {"html": html, "project_id": project_id, "version": version or "latest"}


@app.post("/analyst/document/finalize", response_model=FinalizeResponse)
async def finalize_document(request: FinalizeRequest = Body(...)):
    start = time.time()
    try:
        doc = editor_agent.finalize_document(request.project_id, request.format)
        elapsed = int((time.time() - start) * 1000)
        return FinalizeResponse(
            document_id=doc.document_id, file_url=doc.file_url, generation_time_ms=elapsed
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/analyst/document/audit/{document_id}", response_model=List[DocumentDraft])
async def get_document_audit(document_id: UUID):
    history = editor_agent.get_audit_history(document_id)
    if not history:
        raise HTTPException(status_code=404, detail="Document audit trail not found.")
    return history


# --- Bulk Export Asynchronous Logic ---


async def run_bulk_export(job_id: str, filters: Dict[str, Any]):
    """Simulate long-running export task."""
    export_jobs[job_id]["status"] = "processing"
    # Simulate processing delay
    await asyncio.sleep(5)

    # Simulate finding matching projects and generating files
    export_jobs[job_id]["status"] = "completed"
    export_jobs[job_id]["download_url"] = f"https://storage.ordinoxai.com/exports/{job_id}.zip"
    export_jobs[job_id]["completed_at"] = time.time()


@app.post("/analyst/export/bulk", response_model=BulkExportResponse)
async def trigger_bulk_export(request: BulkExportRequest, background_tasks: BackgroundTasks):
    job_id = f"EXPORT-{uuid4().hex[:8].upper()}"
    export_jobs[job_id] = {
        "status": "queued",
        "created_at": time.time(),
        "filters": request.project_filters,
    }
    background_tasks.add_task(run_bulk_export, job_id, request.project_filters)
    return BulkExportResponse(job_id=job_id, status_url=f"/analyst/export/status/{job_id}")


@app.get("/analyst/export/status/{job_id}")
async def get_export_status(job_id: str):
    job = export_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found.")
    return job


@app.get("/analyst/status")
async def health_check():
    return {"status": "healthy", "service": "analyst-agent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
