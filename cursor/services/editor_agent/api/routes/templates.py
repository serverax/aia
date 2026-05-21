from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.editor_agent.services.models import RenderTemplateRequest
from services.editor_agent.services.template_service import TemplateService

router = APIRouter(prefix="/api/v1", tags=["templates"])


def get_template_service() -> TemplateService:
    from services.editor_agent.api.routes.documents import TEMPLATE_SERVICE

    return TEMPLATE_SERVICE


@router.get("/templates")
def list_templates():
    service = get_template_service()
    return [template.model_dump() for template in service.load_all_templates()]


@router.post("/templates/{template_id}/render")
def render_template(template_id: str, request: RenderTemplateRequest):
    service = get_template_service()
    try:
        template = service.get_template(template_id)
        service.validate_content(template, request.content)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    preview_parts = [f"<h2>{template.name}</h2>"]
    for section in template.sections:
        value = request.content.get(section.field, section.placeholder or "")
        preview_parts.append(f"<h3>{section.field}</h3><p>{value}</p>")
    return {"preview_html": "".join(preview_parts)}

