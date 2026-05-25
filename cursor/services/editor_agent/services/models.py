from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TemplateSection(BaseModel):
    type: Literal["title", "text", "table", "references"]
    field: str
    required: bool = False
    placeholder: str | None = None
    columns: list[str] | None = None
    rows: str | int | None = None
    source: str | None = None


class TemplateStyling(BaseModel):
    font: str = "Arial"
    font_size: int = 11
    line_spacing: float = 1.15
    colors: dict[str, str] = Field(default_factory=dict)


class Template(BaseModel):
    id: str
    name: str
    version: str
    description: str
    sections: list[TemplateSection]
    styling: TemplateStyling


class PolicyReference(BaseModel):
    id: str
    title: str
    url: str | None = None
    jurisdiction: str | None = None


class GenerateDocumentRequest(BaseModel):
    template_id: str
    content: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    format: Literal["docx", "pdf"]


class RenderTemplateRequest(BaseModel):
    content: dict[str, Any]
