from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from services.editor_agent.generator.docx_generator import DocxGenerator
from services.editor_agent.generator.markdown_to_html import render_markdown_to_html
from services.editor_agent.generator.pdf_generator import PdfGenerator
from services.editor_agent.generator.schema_validator import validate_against_template
from services.editor_agent.services.models import GenerateDocumentRequest
from services.editor_agent.services.template_service import TemplateService


class DocumentService:
    def __init__(self, template_service: TemplateService, generated_docs_dir: Path):
        self.template_service = template_service
        self.generated_docs_dir = generated_docs_dir
        self.generated_docs_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: GenerateDocumentRequest) -> dict:
        template = self.template_service.get_template(request.template_id)
        validate_against_template(template, request.content)

        if request.format == "docx":
            generator = DocxGenerator(template)
        else:
            generator = PdfGenerator(template)

        doc_bytes = generator.generate(request.content)
        doc_id = str(uuid.uuid4())
        output_path = self.generated_docs_dir / f"{doc_id}.{request.format}"
        output_path.write_bytes(doc_bytes)

        preview_html = self._build_preview_html(request.content)

        return {
            "id": doc_id,
            "template_id": request.template_id,
            "format": request.format,
            "file_url": f"/api/v1/documents/{doc_id}/download",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "size_bytes": len(doc_bytes),
            "preview_html": preview_html,
        }

    def resolve_document_path(self, doc_id: str) -> Path:
        matches = list(self.generated_docs_dir.glob(f"{doc_id}.*"))
        if not matches:
            raise FileNotFoundError(f"Document {doc_id} not found")
        return matches[0]

    def _build_preview_html(self, content: dict) -> str:
        lines = []
        for key, value in content.items():
            if isinstance(value, str):
                lines.append(f"<h3>{key}</h3>{render_markdown_to_html(value)}")
            else:
                lines.append(f"<h3>{key}</h3><pre>{value}</pre>")
        return "".join(lines)

