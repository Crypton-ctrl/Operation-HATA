from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import models as m
from app.utils.serializers import _row

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(db: Session = Depends(get_db), limit: int = 30):
    rows = db.query(m.Notification).order_by(m.Notification.created_at.desc()).limit(limit).all()
    return [_row(r) for r in rows]


@router.post("/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db)):
    n = db.query(m.Notification).filter_by(id=notification_id).first()
    if n:
        n.read = True
        db.commit()
    return {"status": "ok"}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db)):
    db.query(m.Notification).filter_by(read=False).update({"read": True})
    db.commit()
    return {"status": "ok"}
