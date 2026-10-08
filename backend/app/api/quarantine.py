"""
Quarantine API
Lists quarantined attachments and allows explicit, confirmed destructive
actions. Dangerous files are never automatically restored.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.session import get_db
from app.models import models as m
from app.schemas.schemas import QuarantineActionRequest

router = APIRouter(prefix="/api/quarantine", tags=["quarantine"])


@router.get("")
def list_quarantine(db: Session = Depends(get_db)):
    items = db.query(m.QuarantineItem).order_by(m.QuarantineItem.created_at.desc()).all()
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
            "source": att.source if att else None,
        })
    return result


@router.delete("/{item_id}")
def delete_quarantine_item(item_id: str, payload: QuarantineActionRequest, db: Session = Depends(get_db)):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Destructive action requires explicit confirmation (confirm=true).")
    item = db.query(m.QuarantineItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Quarantine item not found.")

    scan = item.scan
    if scan and scan.attachment and scan.attachment.stored_path:
        try:
            Path(scan.attachment.stored_path).unlink(missing_ok=True)
        except Exception:
            pass

    item.status = "deleted"
    item.resolved_at = datetime.utcnow()
    db.commit()
    return {"status": "deleted", "id": item_id}


@router.post("/{item_id}/restore")
def restore_quarantine_item(item_id: str, payload: QuarantineActionRequest, db: Session = Depends(get_db)):
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Restoring a quarantined file requires explicit confirmation (confirm=true).")
    item = db.query(m.QuarantineItem).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Quarantine item not found.")
    if item.risk_category == "CRITICAL":
        raise HTTPException(status_code=403, detail="CRITICAL-risk files cannot be restored through this interface.")

    item.status = "restored"
    item.resolved_at = datetime.utcnow()
    db.commit()
    return {"status": "restored", "id": item_id}
