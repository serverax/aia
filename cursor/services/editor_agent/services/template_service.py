from __future__ import annotations

import json
from pathlib import Path

from services.editor_agent.services.models import Template


class TemplateService:
    def __init__(self, template_dir: Path):
        self.template_dir = template_dir

    def load_all_templates(self) -> list[Template]:
        templates: list[Template] = []
        for file in sorted(self.template_dir.glob("*.json")):
            with file.open("r", encoding="utf-8") as handle:
                templates.append(Template(**json.load(handle)))
        return templates

    def get_template(self, template_id: str) -> Template:
        template_path = self.template_dir / f"{template_id}.json"
        if not template_path.exists():
            raise FileNotFoundError(f"Template {template_id} not found")
        with template_path.open("r", encoding="utf-8") as handle:
            return Template(**json.load(handle))

    def validate_content(self, template: Template, content: dict) -> None:
        for section in template.sections:
            if section.required and section.field not in content:
                raise ValueError(f"Missing required field: {section.field}")

