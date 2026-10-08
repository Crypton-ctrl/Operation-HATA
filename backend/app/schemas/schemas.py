"""
Pydantic Schemas for request validation. Most read responses are serialized
via helper functions in app/utils/serializers.py to avoid duplicating the
full ORM shape twice; these schemas cover request bodies and simple inputs.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any


class EmailConnectRequest(BaseModel):
    email_address: EmailStr
    app_password: str
    provider: str = "gmail"


class MonitoringIntervalRequest(BaseModel):
    interval_seconds: int = 60


class SettingsUpdateRequest(BaseModel):
    max_upload_mb: Optional[int] = None
    enabled_modules: Optional[Dict[str, bool]] = None
    risk_thresholds: Optional[Dict[str, int]] = None
    scoring_weights: Optional[Dict[str, int]] = None
    notifications_enabled: Optional[bool] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None


class QuarantineActionRequest(BaseModel):
    confirm: bool = False
