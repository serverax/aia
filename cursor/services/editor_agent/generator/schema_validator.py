from __future__ import annotations

from services.editor_agent.services.models import Template


def validate_against_template(template: Template, content: dict) -> None:
    for section in template.sections:
        if section.required and section.field not in content:
            raise ValueError(f"Missing required field: {section.field}")
