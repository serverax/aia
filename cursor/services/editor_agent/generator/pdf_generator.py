from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from services.editor_agent.services.models import Template


class PdfGenerator:
    def __init__(self, template: Template):
        self.template = template

    def generate(self, content: dict) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        for section in self.template.sections:
            value = content.get(section.field, "")

            if section.type == "title":
                title_style = ParagraphStyle(
                    "CustomTitle",
                    parent=styles["Heading1"],
                    fontSize=18,
                    textColor=colors.HexColor(
                        self.template.styling.colors.get("header", "#003366")
                    ),
                    spaceAfter=12,
                )
                story.append(Paragraph(str(value), title_style))

            elif section.type == "text":
                story.append(Paragraph(str(value).replace("\n", "<br/>"), styles["Normal"]))
                story.append(Spacer(1, 0.2 * inch))

            elif section.type == "table":
                story.append(
                    self._build_table(
                        section.columns or [], value if isinstance(value, list) else []
                    )
                )
                story.append(Spacer(1, 0.15 * inch))

            elif section.type == "references":
                story.append(Paragraph("References", styles["Heading3"]))
                for policy in value if isinstance(value, list) else []:
                    story.append(
                        Paragraph(
                            f"- {policy.get('title', 'Untitled policy')} ({policy.get('jurisdiction', 'N/A')})",
                            styles["Normal"],
                        )
                    )

        doc.build(story)
        return buffer.getvalue()

    def _build_table(self, columns: list[str], rows: list[dict]):
        if not columns:
            return Paragraph("No table columns defined.", getSampleStyleSheet()["Normal"])

        data = [columns]
        for row in rows:
            data.append([str(row.get(column, "")) for column in columns])

        table = Table(data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e2f3")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        return table
