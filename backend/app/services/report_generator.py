"""
Report Generator
Produces a professional, branded PDF security report from a completed scan's
full evidence set using ReportLab.
"""
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from app.config import get_settings

settings = get_settings()

RISK_COLORS = {
    "SAFE": colors.HexColor("#22c55e"),
    "LOW": colors.HexColor("#38bdf8"),
    "MEDIUM": colors.HexColor("#eab308"),
    "HIGH": colors.HexColor("#f97316"),
    "CRITICAL": colors.HexColor("#ef4444"),
    "UNKNOWN": colors.HexColor("#94a3b8"),
}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="HataTitle", fontSize=22, leading=26, textColor=colors.HexColor("#0891b2"),
                               spaceAfter=4, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="HataSubtitle", fontSize=11, textColor=colors.HexColor("#475569"),
                               spaceAfter=14))
    styles.add(ParagraphStyle(name="SectionHeader", fontSize=13, textColor=colors.HexColor("#0f172a"),
                               spaceBefore=16, spaceAfter=6, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Body", fontSize=9.5, leading=13.5, textColor=colors.HexColor("#1e293b")))
    return styles


def _kv_table(rows, col_widths=(160, 340)):
    data = [[Paragraph(f"<b>{k}</b>", getSampleStyleSheet()["BodyText"]), str(v)] for k, v in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
    ]))
    return t


def generate_pdf_report(scan_data: dict, output_path: Path) -> Path:
    """
    scan_data is a flat dict assembled by the reports API with keys:
    scan, attachment, email, signature, hashes, metadata, entropy, stego,
    embedded, yara, ocr, qr, url_results, risk, ai_report
    """
    styles = _styles()
    doc = SimpleDocTemplate(str(output_path), pagesize=letter,
                             leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=50)
    story = []

    risk = scan_data.get("risk", {})
    category = risk.get("category", "UNKNOWN")
    risk_color = RISK_COLORS.get(category, RISK_COLORS["UNKNOWN"])

    # --- Header / branding ---
    story.append(Paragraph("OPERATION HATA", styles["HataTitle"]))
    story.append(Paragraph("Hidden Attachment Threat Analyzer &mdash; AI-Powered Security Report", styles["HataSubtitle"]))

    scan = scan_data.get("scan", {})
    story.append(_kv_table([
        ("Scan ID", scan.get("id", "-")),
        ("Report Generated", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")),
        ("Source", scan.get("source", "-").upper()),
    ]))
    story.append(Spacer(1, 10))

    # --- Risk banner ---
    risk_table = Table([[Paragraph(
        f"<font color='white'><b>RISK LEVEL: {category}</b></font>", styles["Body"]),
        Paragraph(f"<font color='white'><b>{risk.get('total_score', 0)}/100</b></font>", styles["Body"])]],
        colWidths=(370, 130))
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 14))

    # --- 1. Executive Summary ---
    ai = scan_data.get("ai_report") or {}
    story.append(Paragraph("1. Executive Summary", styles["SectionHeader"]))
    story.append(Paragraph(ai.get("executive_summary", "No summary available."), styles["Body"]))

    # --- 2. File Information ---
    att = scan_data.get("attachment", {})
    story.append(Paragraph("2. File Information", styles["SectionHeader"]))
    story.append(_kv_table([
        ("Original Filename", att.get("original_filename", "-")),
        ("Size", f"{att.get('size_bytes', 0):,} bytes"),
        ("Declared MIME", att.get("content_type_declared") or "-"),
        ("Source", att.get("source", "-")),
    ]))

    # --- 3. Email Information ---
    email = scan_data.get("email")
    story.append(Paragraph("3. Email Information", styles["SectionHeader"]))
    if email:
        story.append(_kv_table([
            ("Sender", email.get("sender", "-")),
            ("Subject", email.get("subject", "-")),
            ("Received", email.get("received_at", "-")),
        ]))
    else:
        story.append(Paragraph("This attachment was submitted via manual upload; no associated email.", styles["Body"]))

    # --- 4. Security Findings / 5. Metadata ---
    story.append(Paragraph("4. File Signature Analysis", styles["SectionHeader"]))
    sig = scan_data.get("signature", {})
    story.append(_kv_table([
        ("Extension", sig.get("extension", "-")),
        ("Detected Format", sig.get("detected_format", "-")),
        ("Consistent", "Yes" if sig.get("extension_mime_consistent") else "No"),
        ("Status", sig.get("status", "-")),
    ]))

    story.append(Paragraph("5. Metadata Analysis", styles["SectionHeader"]))
    meta = scan_data.get("metadata", {})
    story.append(_kv_table([
        ("Camera Make/Model", f"{meta.get('camera_make') or '-'} / {meta.get('camera_model') or '-'}"),
        ("Software", meta.get("software") or "-"),
        ("Dimensions", f"{meta.get('width', '-')} x {meta.get('height', '-')}"),
        ("GPS Present", "Yes" if meta.get("gps_present") else "No"),
        ("Anomalies", str(len(meta.get("anomalies", []))) + " found" if meta.get("anomaly_detected") else "None"),
    ]))

    story.append(Paragraph("6. Entropy Analysis", styles["SectionHeader"]))
    ent = scan_data.get("entropy", {})
    story.append(_kv_table([
        ("Overall Entropy", f"{ent.get('overall_entropy', '-')} bits/byte"),
        ("Tail Entropy", f"{ent.get('tail_entropy', '-')} bits/byte"),
        ("Classification", ent.get("classification", "-")),
    ]))
    story.append(Paragraph(
        "Note: high entropy alone does not prove malicious content - it is one signal among several.",
        styles["Body"]))

    story.append(Paragraph("7. Steganography Analysis", styles["SectionHeader"]))
    stego = scan_data.get("stego", {})
    story.append(_kv_table([
        ("Classification", stego.get("classification", "-")),
        ("LSB Score", stego.get("lsb_score", "-")),
        ("Chi-Square Score", stego.get("chi_square_score", "-")),
    ]))
    story.append(Paragraph(stego.get("notes", ""), styles["Body"]))

    story.append(Paragraph("8. Appended / Embedded Data Analysis", styles["SectionHeader"]))
    emb = scan_data.get("embedded", {})
    story.append(_kv_table([
        ("Appended Data Found", "Yes" if emb.get("appended_data_found") else "No"),
        ("Offset", emb.get("appended_data_offset", "-")),
        ("Size", emb.get("appended_data_size", "-")),
        ("Embedded Signatures", ", ".join(s["type"] for s in emb.get("embedded_signatures", [])) or "None"),
    ]))

    story.append(Paragraph("9. YARA Results", styles["SectionHeader"]))
    yara = scan_data.get("yara", {})
    story.append(_kv_table([
        ("Rules Scanned", yara.get("rules_scanned", 0)),
        ("Matches", len(yara.get("matches", []))),
        ("Engine Available", "Yes" if yara.get("engine_available") else "No"),
    ]))
    for m in yara.get("matches", []):
        story.append(Paragraph(f"&bull; <b>{m['rule']}</b> ({m['severity']}): {m['description']}", styles["Body"]))

    story.append(Paragraph("10. Hash Information", styles["SectionHeader"]))
    hashes = scan_data.get("hashes", {})
    story.append(_kv_table([
        ("SHA-256", hashes.get("sha256", "-")),
        ("SHA-1", hashes.get("sha1", "-")),
        ("MD5", hashes.get("md5", "-")),
        ("External Reputation", hashes.get("virustotal_status", "not_configured")),
    ]))

    story.append(Paragraph("11. OCR Findings", styles["SectionHeader"]))
    ocr = scan_data.get("ocr", {})
    if ocr.get("engine_available"):
        story.append(Paragraph(f"Suspicious phrases: {', '.join(ocr.get('suspicious_phrases', [])) or 'None'}", styles["Body"]))
    else:
        story.append(Paragraph("OCR analysis unavailable.", styles["Body"]))

    story.append(Paragraph("12. QR Findings", styles["SectionHeader"]))
    qr = scan_data.get("qr", {})
    if qr.get("engine_available"):
        if qr.get("qr_codes"):
            for q in qr["qr_codes"]:
                story.append(Paragraph(f"&bull; [{q['type']}] {q['content'][:100]} - Risk: {q['risk']}", styles["Body"]))
        else:
            story.append(Paragraph("No QR codes detected.", styles["Body"]))
    else:
        story.append(Paragraph("QR analysis unavailable.", styles["Body"]))

    story.append(Paragraph("13. URL Findings", styles["SectionHeader"]))
    url_results = scan_data.get("url_results", [])
    if url_results:
        for u in url_results:
            story.append(Paragraph(f"&bull; {u['url'][:90]} - Risk: {u['risk_level']}", styles["Body"]))
    else:
        story.append(Paragraph("No URLs discovered via OCR or QR analysis.", styles["Body"]))

    story.append(PageBreak())

    story.append(Paragraph("14-16. Risk Score, Explanation & Recommendation", styles["SectionHeader"]))
    story.append(_kv_table([
        ("Risk Score", f"{risk.get('total_score', 0)}/100"),
        ("Risk Category", category),
    ]))
    for f in risk.get("contributing_factors", []):
        story.append(Paragraph(f"&bull; {f['factor']} (+{f['points']} pts) - {f['reason']}", styles["Body"]))

    story.append(Paragraph("17. AI Security Assessment", styles["SectionHeader"]))
    story.append(Paragraph(f"<b>Assessment:</b> {ai.get('assessment', '-')}", styles["Body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Likely Scenario:</b> {ai.get('likely_scenario', '-')}", styles["Body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Recommendation:</b> {ai.get('recommendation', '-')}", styles["Body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Confidence:</b> {ai.get('confidence', '-')}", styles["Body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Limitations:</b> {ai.get('limitations', '-')}", styles["Body"]))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Generated by Operation HATA - Hidden Attachment Threat Analyzer. "
        "This report is generated for security triage purposes and should be reviewed by a qualified analyst.",
        styles["Body"]))

    doc.build(story)
    return output_path
