"""
Emails API
Manages the connected email account (secure app-password based IMAP for the
reference implementation), monitoring lifecycle, and manual sync.
Credentials are encrypted before storage and never returned to the frontend.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import models as m
from app.schemas.schemas import EmailConnectRequest, MonitoringIntervalRequest
from app.utils.crypto import encrypt_credential
from app.services import email_monitor
from app.config import get_settings

router = APIRouter(prefix="/api/emails", tags=["emails"])
settings = get_settings()


@router.get("/status")
def email_status(db: Session = Depends(get_db)):
    account = db.query(m.EmailAccount).first()
    if not account:
        return {
            "connected": False, "email_address": None, "monitoring_active": False,
            "last_sync_at": None, "emails_checked": 0, "attachments_analyzed": 0,
        }
    return {
        "connected": account.connected,
        "email_address": account.email_address,
        "monitoring_active": account.monitoring_active,
        "last_sync_at": account.last_sync_at,
        "emails_checked": account.emails_checked,
        "attachments_analyzed": account.attachments_analyzed,
        "poll_interval_seconds": account.poll_interval_seconds,
    }


import imaplib

@router.post("/connect")
def connect_email(payload: EmailConnectRequest, db: Session = Depends(get_db)):
    """Connects via IMAP with an app-specific password (never stored in plaintext).
    For Gmail, this must be a 16-character App Password generated with 2FA enabled -
    the regular account password will not work and is never requested."""
    
    # Test the connection before saving
    try:
        imap = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
        imap.login(payload.email_address, payload.app_password)
        imap.logout()
    except imaplib.IMAP4.error as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed. Please check your email and app password. Details: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect to email provider. Details: {e}")

    account = db.query(m.EmailAccount).first()
    encrypted = encrypt_credential(payload.app_password)

    if account:
        account.email_address = payload.email_address
        account.provider = payload.provider
        account.auth_method = "imap_app_password"
        account.encrypted_credential = encrypted
        account.connected = True
    else:
        account = m.EmailAccount(
            email_address=payload.email_address, provider=payload.provider,
            auth_method="imap_app_password", encrypted_credential=encrypted, connected=True,
        )
        db.add(account)
    db.commit()
    db.refresh(account)
    return {"connected": True, "email_address": account.email_address}


@router.post("/disconnect")
def disconnect_email(db: Session = Depends(get_db)):
    account = db.query(m.EmailAccount).first()
    if account:
        if account.monitoring_active:
            email_monitor.stop_monitoring(account.id)
        account.connected = False
        account.monitoring_active = False
        account.encrypted_credential = None
        db.commit()
    return {"connected": False}


@router.post("/start-monitoring")
async def start_monitoring(payload: MonitoringIntervalRequest, db: Session = Depends(get_db)):
    account = db.query(m.EmailAccount).first()
    if not account or not account.connected:
        raise HTTPException(status_code=400, detail="No connected email account. Connect one first.")
    account.poll_interval_seconds = payload.interval_seconds
    account.monitoring_active = True
    db.commit()
    email_monitor.start_monitoring(account.id, payload.interval_seconds)
    return {"monitoring_active": True}


@router.post("/stop-monitoring")
async def stop_monitoring(db: Session = Depends(get_db)):
    account = db.query(m.EmailAccount).first()
    if account:
        account.monitoring_active = False
        db.commit()
        email_monitor.stop_monitoring(account.id)
    return {"monitoring_active": False}


@router.post("/sync-now")
async def sync_now(db: Session = Depends(get_db)):
    account = db.query(m.EmailAccount).first()
    if not account or not account.connected:
        raise HTTPException(status_code=400, detail="No connected email account.")
    await email_monitor.sync_now(account.id)
    return {"status": "sync_complete"}
