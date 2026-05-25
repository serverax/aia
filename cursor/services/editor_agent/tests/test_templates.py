from pathlib import Path

from services.editor_agent.services.template_service import TemplateService


def test_load_all_templates():
    service = TemplateService(Path(__file__).resolve().parents[1] / "templates")
    templates = service.load_all_templates()
    assert len(templates) >= 5


def test_validate_content_required_fields():
    service = TemplateService(Path(__file__).resolve().parents[1] / "templates")
    template = service.get_template("risk_assessment")
    content = {
        "title": "Q2 Assessment",
        "executive_summary": "Summary",
        "recommendations": "Do work",
    }
    service.validate_content(template, content)
