from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.editor_agent.services.document_service import DocumentService
from services.editor_agent.services.models import GenerateDocumentRequest
from services.editor_agent.services.template_service import TemplateService

BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATE_SERVICE = TemplateService(BASE_DIR / "templates")
DOCUMENT_SERVICE = DocumentService(TEMPLATE_SERVICE, BASE_DIR / "generated_docs")

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.post("/generate/{format}")
def generate_document(format: str, request: GenerateDocumentRequest):
    try:
        payload = request.model_copy(update={"format": format})
        return DOCUMENT_SERVICE.generate(payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: str):
    try:
        file_path = DOCUMENT_SERVICE.resolve_document_path(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if file_path.suffix == ".docx"
        else "application/pdf"
    )
    return FileResponse(path=file_path, filename=file_path.name, media_type=media_type)

