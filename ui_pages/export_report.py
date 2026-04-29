"""
Export utilities for TrustLLM evaluation reports.
Supports CSV, JSON, and PDF formats.
"""

import json
import io
from datetime import datetime
import pandas as pd
import streamlit as st


def export_csv(results, df_raw, dataset_name: str, timestamp: str):
    """Export results as CSV."""
    export_df = df_raw[["_prompt_full", "_expected_full", "_answer_full", "Similarity", "_passed", "Latency (s)"]].copy()
    export_df.columns = ["Prompt", "Expected Answer", "Model Answer", "Similarity", "Passed", "Latency (s)"]
    export_df["Similarity"] = export_df["Similarity"].apply(lambda x: f"{x:.2%}")
    
    output = io.StringIO()
    export_df.to_csv(output, index=False)
    csv_data = output.getvalue()
    
    filename = f"trustllm_{dataset_name}_{timestamp}.csv"
    st.download_button(
        label="📥 Download CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
        key="download_csv"
    )


def export_json(results, model: str, dataset_name: str, timestamp: str, pass_rate: float, hall_rate: float, avg_sim: float, avg_lat: float):
    """Export results as JSON."""
    report_data = {
        "metadata": {
            "dataset": dataset_name,
            "model": model,
            "generated_at": datetime.now().isoformat(),
            "total_prompts": len(results),
            "passed": sum(1 for r in results if r.get("passed")),
            "failed": sum(1 for r in results if not r.get("passed")),
            "accuracy": f"{pass_rate:.0%}",
            "hallucination_rate": f"{hall_rate:.0%}",
            "avg_similarity": f"{avg_sim:.2%}",
            "avg_latency_s": round(avg_lat, 2)
        },
        "results": [
            {
                "prompt": r["prompt"],
                "expected_answer": r["expected_answer"],
                "model_answer": r["model_answer"],
                "similarity": f"{r.get('similarity', 0):.2%}" if r.get('similarity') else None,
                "passed": r["passed"],
                "latency_s": r["latency_s"]
            }
            for r in results
        ]
    }
    
    json_data = json.dumps(report_data, indent=2)
    filename = f"trustllm_{dataset_name}_{timestamp}.json"
    st.download_button(
        label="📥 Download JSON",
        data=json_data,
        file_name=filename,
        mime="application/json",
        key="download_json"
    )


def export_pdf(results, model: str, dataset_name: str, timestamp: str, pass_rate: float, hall_rate: float, avg_sim: float, avg_lat: float, total_results: int):
    """Export results as PDF."""
    try:
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        st.error(
            "To export to PDF, install reportlab:\n\n"
            "```bash\n"
            "pip install reportlab\n"
            "```"
        )
        return

    pdf_buffer = io.BytesIO()
    # Use landscape for more horizontal space
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()

    # Cell text style — small font, word-wrapping
    cell_style = ParagraphStyle(
        "CellStyle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        wordWrap="CJK",
    )
    header_cell_style = ParagraphStyle(
        "HeaderCell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.whitesmoke,
        fontName="Helvetica-Bold",
    )
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=10,
        fontName="Helvetica-Bold",
    )

    content = []

    # Title
    content.append(Paragraph("TrustLLM Evaluation Report", title_style))
    content.append(Spacer(1, 0.15 * inch))

    # Summary table
    content.append(Paragraph("Report Summary", section_style))
    metadata_data = [
        ["Dataset", dataset_name],
        ["Model", model],
        ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Total Prompts", str(total_results)],
        ["Accuracy", f"{pass_rate:.0%}"],
        ["Failed", str(total_results - sum(1 for r in results if r.get("passed")))],
        ["Hallucination Rate", f"{hall_rate:.0%}"],
        ["Avg Similarity", f"{avg_sim:.2%}"],
        ["Avg Latency", f"{avg_lat:.1f}s"],
    ]
    metadata_table = Table(metadata_data, colWidths=[2 * inch, 4 * inch])
    metadata_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR",     (0, 0), (-1, -1), colors.black),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    content.append(metadata_table)
    content.append(Spacer(1, 0.3 * inch))

    # Detailed results table
    content.append(Paragraph(f"Detailed Results ({min(len(results), 50)} prompts)", section_style))

    # Column widths in points (landscape letter = 11in wide, minus 1in margins = 10in usable)
    col_widths = [0.3 * inch, 2.5 * inch, 2.5 * inch, 2.4 * inch, 0.7 * inch, 0.55 * inch, 0.65 * inch]

    # Header row using Paragraphs for consistency
    header_labels = ["#", "Prompt", "Expected Answer", "Model Answer", "Similarity", "Status", "Latency"]
    table_data = [[Paragraph(h, header_cell_style) for h in header_labels]]

    for i, r in enumerate(results[:50], 1):
        def _p(text, max_chars=300):
            """Wrap text in a Paragraph, truncating if too long."""
            text = str(text or "").strip()
            if len(text) > max_chars:
                text = text[:max_chars] + "…"
            return Paragraph(text, cell_style)

        sim_val = r.get("similarity")
        table_data.append([
            Paragraph(str(i), cell_style),
            _p(r["prompt"]),
            _p(r["expected_answer"]),
            _p(r["model_answer"]),
            Paragraph(f"{sim_val:.0%}" if sim_val is not None else "—", cell_style),
            Paragraph("Pass" if r["passed"] else "Fail", cell_style),
            Paragraph(f"{r['latency_s']:.2f}s", cell_style),
        ])

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#2563eb")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.whitesmoke),
        # Body alternating rows
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        # Alignment
        ("ALIGN",         (0, 0), (0, -1),  "CENTER"),   # # col centred
        ("ALIGN",         (4, 0), (6, -1),  "CENTER"),   # sim / status / latency centred
        ("ALIGN",         (1, 0), (3, -1),  "LEFT"),     # text cols left
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        # Font
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        # Padding
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("LINEBELOW",     (0, 0), (-1, 0),  1.0, colors.HexColor("#1d4ed8")),
    ]))
    content.append(table)
    content.append(Spacer(1, 0.2 * inch))

    # Footer
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
    )
    content.append(Paragraph(
        f"Report generated by TrustLLM  \u2022  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        footer_style,
    ))

    doc.build(content)
    pdf_data = pdf_buffer.getvalue()

    filename = f"trustllm_{dataset_name}_{timestamp}.pdf"
    st.download_button(
        label="📥 Download PDF",
        data=pdf_data,
        file_name=filename,
        mime="application/pdf",
        key="download_pdf",
    )
