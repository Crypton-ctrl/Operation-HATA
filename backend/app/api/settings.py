from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import models as m
from app.schemas.schemas import SettingsUpdateRequest
from app.utils.serializers import _row
from app.config import get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])
app_settings = get_settings()


def _get_or_create(db: Session) -> m.UserSettings:
    row = db.query(m.UserSettings).filter_by(id="SETTINGS-DEFAULT").first()
    if not row:
        row = m.UserSettings(id="SETTINGS-DEFAULT")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("")
def get_settings_route(db: Session = Depends(get_db)):
    row = _get_or_create(db)
    data = _row(row)
    # Never expose whether/what API keys are set beyond a boolean flag
    data["ai_api_key_configured"] = bool(app_settings.AI_API_KEY)
    data["virustotal_api_key_configured"] = bool(app_settings.VIRUSTOTAL_API_KEY)
    return data


@router.post("")
def update_settings_route(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    row = _get_or_create(db)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    data = _row(row)
    data["ai_api_key_configured"] = bool(app_settings.AI_API_KEY)
    data["virustotal_api_key_configured"] = bool(app_settings.VIRUSTOTAL_API_KEY)
    return data
