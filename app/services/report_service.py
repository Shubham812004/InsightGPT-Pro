# app/services/report_service.py
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io import BytesIO
import plotly.io as pio
import json

def generate_report_from_history(chat_history: list) -> bytes:
    """
    Generates a PDF report from the conversation history.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, rightMargin=inch/2, leftMargin=inch/2, topMargin=inch/2, bottomMargin=inch/2)

    styles = getSampleStyleSheet()
    story = []

    # Add Title
    title = Paragraph("InsightGPT Pro: Analysis Report", styles['h1'])
    story.append(title)
    story.append(Spacer(1, 0.2*inch))

    # Add conversation history
    for message in chat_history:
        role = message.get("role")
        content = message.get("content").replace('\n', '<br/>')

        if role == "user":
            p = Paragraph(f"<b>You:</b> {content}", styles['BodyText'])
            story.append(p)
        elif role == "assistant":
            p = Paragraph(f"<b>InsightGPT Pro:</b> {content}", styles['BodyText'])
            story.append(p)

            # Check for and add chart
            if "chart" in message:
                chart_json = message.get("chart")
                try:
                    fig = pio.from_json(chart_json)
                    # Save the figure to a byte buffer as a PNG image
                    img_buffer = BytesIO()
                    fig.write_image(img_buffer, format='png', width=800, height=500, scale=2)
                    img_buffer.seek(0)

                    # Add image to the PDF
                    img = Image(img_buffer, width=6*inch, height=3.75*inch)
                    story.append(Spacer(1, 0.1*inch))
                    story.append(img)
                    story.append(Spacer(1, 0.1*inch))
                except Exception as e:
                    print(f"Failed to add chart to PDF: {e}")

        story.append(Spacer(1, 0.2*inch))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes