"""
Serializers - convert SQLAlchemy scan objects (with all related analysis
results) into plain dicts for API responses and PDF generation.
"""


def _row(obj):
    if obj is None:
        return None
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    return d


def serialize_scan_summary(scan) -> dict:
    att = scan.attachment
    email = att.email if att else None
    return {
        "id": scan.id,
        "status": scan.status,
        "current_stage": scan.current_stage,
        "source": scan.source,
        "risk_score": scan.risk_score,
        "risk_category": scan.risk_category,
        "started_at": scan.started_at,
        "completed_at": scan.completed_at,
        "filename": att.original_filename if att else None,
        "sender": email.sender if email else None,
        "subject": email.subject if email else None,
    }


def serialize_scan_full(scan) -> dict:
    att = scan.attachment
    email = att.email if att else None
    return {
        "scan": _row(scan),
        "attachment": _row(att),
        "email": _row(email),
        "signature": _row(scan.signature_result),
        "hashes": _row(scan.file_hashes),
        "metadata": _row(scan.metadata_result),
        "entropy": _row(scan.entropy_result),
        "stego": _row(scan.stego_result),
        "embedded": _row(scan.embedded_content),
        "yara": _row(scan.yara_result),
        "ocr": _row(scan.ocr_result),
        "qr": _row(scan.qr_result),
        "url_results": [_row(u) for u in scan.url_results],
        "risk": _row(scan.risk_assessment),
        "ai_report": _row(scan.ai_report),
        "quarantine_item": _row(scan.quarantine_item),
    }
