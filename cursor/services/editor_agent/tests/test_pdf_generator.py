from pathlib import Path

from services.editor_agent.generator.pdf_generator import PdfGenerator
from services.editor_agent.services.template_service import TemplateService


def test_pdf_generator_returns_bytes():
    service = TemplateService(Path(__file__).resolve().parents[1] / "templates")
    template = service.get_template("policy_memo")
    generator = PdfGenerator(template)

    payload = {
        "title": "Policy Memo",
        "context": "This memo explains policy changes.",
        "recommendations": "Adopt stronger controls.",
        "policies": [{"title": "Information Security Policy", "jurisdiction": "UK"}],
    }

    output = generator.generate(payload)
    assert isinstance(output, bytes)
    assert len(output) > 100

