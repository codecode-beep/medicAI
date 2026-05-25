import logging
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger("medintel")


def generate_medical_report_pdf(
    patient_name: str,
    report_title: str,
    analysis: dict,
    historical_comparison: dict | None = None,
    rag_references: list[str] | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18, spaceAfter=12, textColor=colors.HexColor("#1e40af"))
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=14, spaceAfter=8, textColor=colors.HexColor("#1e3a5f"))
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, spaceAfter=6, leading=14)

    story = []
    story.append(Paragraph("MedIntel AI — Medical Intelligence Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Patient Information", heading_style))
    story.append(Paragraph(f"<b>Name:</b> {patient_name}", body_style))
    story.append(Paragraph(f"<b>Report:</b> {report_title}", body_style))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("AI Summary", heading_style))
    story.append(Paragraph(analysis.get("summary", "N/A"), body_style))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Key Findings", heading_style))
    for finding in analysis.get("findings", []):
        story.append(Paragraph(f"• {finding}", body_style))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Medical Interpretation", heading_style))
    story.append(Paragraph(analysis.get("interpretation", "N/A"), body_style))
    story.append(Spacer(1, 0.15 * inch))

    severity = analysis.get("severity", "unknown")
    severity_color = {"low": "#22c55e", "moderate": "#f59e0b", "high": "#ef4444", "critical": "#dc2626"}.get(severity, "#6b7280")
    story.append(Paragraph(f'Severity Analysis: <font color="{severity_color}"><b>{severity.upper()}</b></font>', heading_style))
    story.append(Spacer(1, 0.15 * inch))

    medicines = analysis.get("medicines", [])
    if medicines:
        story.append(Paragraph("Medications Identified", heading_style))
        med_data = [["Medicine", "Dosage", "Frequency"]]
        for med in medicines:
            med_data.append([med.get("name", ""), med.get("dosage", ""), med.get("frequency", "")])
        t = Table(med_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.15 * inch))

    conditions = analysis.get("conditions", [])
    if conditions:
        story.append(Paragraph("Conditions Identified", heading_style))
        for cond in conditions:
            story.append(Paragraph(f"• {cond}", body_style))
        story.append(Spacer(1, 0.15 * inch))

    if historical_comparison:
        story.append(Paragraph("Historical Comparison", heading_style))
        story.append(Paragraph(historical_comparison.get("summary", str(historical_comparison)), body_style))
        story.append(Spacer(1, 0.15 * inch))

    if rag_references:
        story.append(Paragraph("Medical References (RAG)", heading_style))
        for ref in rag_references[:5]:
            story.append(Paragraph(f"• {ref[:200]}", body_style))
        story.append(Spacer(1, 0.15 * inch))

    recommendations = analysis.get("recommendations", [])
    if recommendations:
        story.append(Paragraph("Recommendations", heading_style))
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", body_style))

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "<i>Disclaimer: This report is AI-generated for informational purposes only. "
        "It is not a substitute for professional medical advice, diagnosis, or treatment. "
        "Always consult a qualified healthcare provider.</i>",
        body_style,
    ))

    doc.build(story)
    return buffer.getvalue()
