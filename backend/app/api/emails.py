import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import models as m
from app.schemas.schemas import MonitoringIntervalRequest
from app.utils.crypto import encrypt_credential
from app.services import email_monitor
from app.config import get_settings
from app.api.auth import require_auth
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

router = APIRouter(prefix="/api/emails", tags=["emails"])
settings = get_settings()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_google_flow():
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth credentials are not configured on the server.")
    client_config = {
        "web": {
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.GMAIL_REDIRECT_URI
    return flow

@router.get("/status")
def email_status(db: Session = Depends(get_db), _: bool = require_auth):
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

@router.get("/oauth-url")
def get_oauth_url(db: Session = Depends(get_db), _: bool = require_auth):
    try:
        flow = get_google_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return {"url": authorization_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/oauth/callback")
def oauth_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    
    frontend_url = settings.CORS_ORIGINS.split(",")[0].strip() if settings.CORS_ORIGINS else "http://localhost:5173"
    redirect_target = f"{frontend_url}/automatic"

    if error:
        return RedirectResponse(url=f"{redirect_target}?error={error}")
    
    if not code:
        return RedirectResponse(url=f"{redirect_target}?error=no_code")

    try:
        flow = get_google_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Retrieve email address using Gmail API
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress')

        # Store credentials securely
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        encrypted = encrypt_credential(json.dumps(creds_data))

        account = db.query(m.EmailAccount).first()
        if account:
            account.email_address = email_address
            account.provider = "gmail"
            account.auth_method = "oauth2"
            account.encrypted_credential = encrypted
            account.connected = True
        else:
            account = m.EmailAccount(
                email_address=email_address, provider="gmail",
                auth_method="oauth2", encrypted_credential=encrypted, connected=True,
            )
            db.add(account)
        db.commit()

        return RedirectResponse(url=f"{redirect_target}?connected=true")
    except Exception as e:
        import traceback
        print(f"OAUTH CALLBACK ERROR: {str(e)}")
        traceback.print_exc()
        return RedirectResponse(url=f"{redirect_target}?error=auth_failed")

@router.post("/disconnect")
def disconnect_email(db: Session = Depends(get_db), _: bool = require_auth):
    account = db.query(m.EmailAccount).first()
    if account:
        if account.monitoring_active:
            email_monitor.stop_monitoring(account.id)
        
        # Revoke token with Google if we have it
        try:
            from app.utils.crypto import decrypt_credential
            import requests
            if account.encrypted_credential:
                creds_json = decrypt_credential(account.encrypted_credential)
                creds_data = json.loads(creds_json)
                token = creds_data.get('token')
                if token:
                    requests.post('https://oauth2.googleapis.com/revoke',
                                  params={'token': token},
                                  headers={'content-type': 'application/x-www-form-urlencoded'})
        except Exception as e:
            pass # Ignore revoke errors

        account.connected = False
        account.monitoring_active = False
        account.encrypted_credential = None
        db.commit()
    return {"connected": False}


@router.post("/start-monitoring")
async def start_monitoring(payload: MonitoringIntervalRequest, db: Session = Depends(get_db), _: bool = require_auth):
    account = db.query(m.EmailAccount).first()
    if not account or not account.connected:
        raise HTTPException(status_code=400, detail="No connected email account. Connect one first.")
    account.poll_interval_seconds = payload.interval_seconds
    account.monitoring_active = True
    db.commit()
    email_monitor.start_monitoring(account.id, payload.interval_seconds)
    return {"monitoring_active": True}


@router.post("/stop-monitoring")
async def stop_monitoring(db: Session = Depends(get_db), _: bool = require_auth):
    account = db.query(m.EmailAccount).first()
    if account:
        account.monitoring_active = False
        db.commit()
        email_monitor.stop_monitoring(account.id)
    return {"monitoring_active": False}


@router.post("/sync-now")
async def sync_now(db: Session = Depends(get_db), _: bool = require_auth):
    account = db.query(m.EmailAccount).first()
    if not account or not account.connected:
        raise HTTPException(status_code=400, detail="No connected email account.")
    await email_monitor.sync_now(account.id)
    return {"status": "sync_complete"}
