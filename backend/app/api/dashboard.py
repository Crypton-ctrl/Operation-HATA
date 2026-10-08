"""
Dashboard API - aggregate statistics for the SOC-style overview page.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.session import get_db
from app.models import models as m
from app.utils.serializers import serialize_scan_summary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(m.Scan.id)).filter(m.Scan.status == "complete").scalar() or 0

    category_counts = {c: 0 for c in ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]}
    rows = db.query(m.Scan.risk_category, func.count(m.Scan.id)).filter(
        m.Scan.status == "complete").group_by(m.Scan.risk_category).all()
    for cat, count in rows:
        if cat in category_counts:
            category_counts[cat] = count

    threats_detected = category_counts["HIGH"] + category_counts["CRITICAL"]
    suspicious = category_counts["MEDIUM"]
    safe = category_counts["SAFE"] + category_counts["LOW"]

    recent = db.query(m.Scan).filter(m.Scan.status == "complete").order_by(
        m.Scan.started_at.desc()).limit(8).all()
    recent_data = [serialize_scan_summary(s) for s in recent]

    recent_threats = db.query(m.Scan).filter(
        m.Scan.status == "complete", m.Scan.risk_category.in_(["HIGH", "CRITICAL"])
    ).order_by(m.Scan.started_at.desc()).limit(5).all()
    recent_threats_data = [serialize_scan_summary(s) for s in recent_threats]

    account = db.query(m.EmailAccount).first()
    monitoring = {
        "connected": bool(account and account.connected),
        "email_address": account.email_address if account else None,
        "monitoring_active": bool(account and account.monitoring_active),
        "last_sync_at": account.last_sync_at if account else None,
        "emails_checked": account.emails_checked if account else 0,
        "attachments_analyzed": account.attachments_analyzed if account else 0,
    }

    latest_scan = db.query(m.Scan).filter(m.Scan.status == "complete").order_by(
        m.Scan.started_at.desc()).first()
    current_risk = {
        "score": latest_scan.risk_score if latest_scan else 0,
        "category": latest_scan.risk_category if latest_scan else "SAFE",
    }

    return {
        "total_scanned": total,
        "threats_detected": threats_detected,
        "suspicious_files": suspicious,
        "safe_files": safe,
        "current_risk": current_risk,
        "distribution": category_counts,
        "recent_attachments": recent_data,
        "recent_threats": recent_threats_data,
        "monitoring": monitoring,
    }
