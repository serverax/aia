from pathlib import Path

from services.editor_agent.generator.docx_generator import DocxGenerator
from services.editor_agent.services.template_service import TemplateService


def test_docx_generator_returns_bytes():
    service = TemplateService(Path(__file__).resolve().parents[1] / "templates")
    template = service.get_template("risk_assessment")
    generator = DocxGenerator(template)

    payload = {
        "title": "Q2 2026 Risk Assessment",
        "executive_summary": "Summary text",
        "risk_matrix": [
            {"Risk": "Data breach", "Probability": "High", "Impact": "Critical", "Score": 9}
        ],
        "recommendations": "Use MFA and rotate keys.",
        "policies": [{"title": "Data Protection Policy", "jurisdiction": "UK"}],
    }

    output = generator.generate(payload)
    assert isinstance(output, bytes)
    assert len(output) > 100
