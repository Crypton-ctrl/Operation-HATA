"""
Quarantine API
Lists quarantined attachments and allows explicit, confirmed destructive
actions. Dangerous files are never automatically restored.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel

from app.database.session import get_db
from app.models import models as m
from app.schemas.schemas import QuarantineActionRequest
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/quarantine", tags=["quarantine"])


class QuarantineManualRequest(BaseModel):
    scan_id: str
    reason: str | None = None


@router.get("")
def list_quarantine(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    query = db.query(m.QuarantineItem)
    if user.role != "admin":
        query = query.filter((m.QuarantineItem.user_id == user.id) | (m.QuarantineItem.user_id.is_(None)))
    items = query.order_by(m.QuarantineItem.created_at.desc()).all()
    result = []
    for item in items:
        scan = item.scan
        att = scan.attachment if scan else None
        result.append({
            "id": item.id,
            "scan_id": item.scan_id,
            "filename": item.filename,
            "sha256": item.sha256,
            "risk_category": item.risk_category,
            "reason": item.reason,
            "status": item.status,
            "created_at": item.created_at,
            "source": att.source if att else "manual",
        })
    return result


@router.post("/manual")
def manual_quarantine(payload: QuarantineManualRequest, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    scan = db.query(m.Scan).filter_by(id=payload.scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if scan.user_id and scan.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    existing = db.query(m.QuarantineItem).filter_by(scan_id=scan.id).first()
    if existing:
        existing.status = "quarantined"
        existing.reason = payload.reason or existing.reason or "Manually quarantined by analyst"
        existing.resolved_at = None
        db.commit()
        return {"status": "quarantined", "id": existing.id}

    attachment = scan.attachment
    hashes = scan.file_hashes
    risk = scan.risk_assessment
    item = m.QuarantineItem(
        scan_id=scan.id,
        filename=attachment.original_filename if attachment else "attachment",
        sha256=(hashes.sha256 if hashes else None) or (attachment.sha256 if attachment else None),
        risk_category=scan.risk_category or (risk.category if risk else "MANUAL"),
        reason=payload.reason or "Manually quarantined by analyst",
        user_id=user.id,
        status="quarantined",
    )
    db.add(item)
    db.commit()
    return {"status": "quarantined", "id": item.id}


@router.delete("/{item_id}")
def delete_quarantine_item(item_id: str, payload: QuarantineActionRequest, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Destructive action requires explicit confirmation (confirm=true).")
    item = db.query(m.QuarantineItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Quarantine item not found.")
    if item.user_id and item.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    scan = item.scan
    if scan and scan.attachment and scan.attachment.stored_path:
        try:
            Path(scan.attachment.stored_path).unlink(missing_ok=True)
        except Exception:
            pass

    item.status = "deleted"
    item.resolved_at = datetime.now()
    db.commit()
    return {"status": "deleted", "id": item_id}


@router.post("/{item_id}/restore")
def restore_quarantine_item(item_id: str, payload: QuarantineActionRequest, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Restoring a quarantined file requires explicit confirmation (confirm=true).")
    item = db.query(m.QuarantineItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Quarantine item not found.")
    if item.user_id and item.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")
    if item.risk_category == "CRITICAL":
        raise HTTPException(status_code=403, detail="CRITICAL-risk files cannot be restored through this interface.")

    item.status = "restored"
    item.resolved_at = datetime.now()
    db.commit()
    return {"status": "restored", "id": item_id}
