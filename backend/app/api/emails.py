import json
import secrets
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import models as m
from app.schemas.schemas import MonitoringIntervalRequest
from app.utils.crypto import encrypt_credential
from app.services import email_monitor
from app.config import get_settings
from app.api.auth import get_current_user, _sessions, hash_password
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

router = APIRouter(prefix="/api/emails", tags=["emails"])
settings = get_settings()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

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
def email_status(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    account = db.query(m.EmailAccount).filter_by(user_id=user.id).first()
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
def get_oauth_url(request: Request, user: m.User = Depends(get_current_user)):
    try:
        flow = get_google_flow()
        origin = request.query_params.get("redirect") or request.headers.get("origin") or ""
        state = f"connect:{user.id}:{origin}"
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        return {"url": authorization_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/oauth-login-url")
def get_oauth_login_url(request: Request):
    try:
        flow = get_google_flow()
        origin = request.query_params.get("redirect") or request.headers.get("origin") or ""
        state = f"login:{origin}"
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/oauth/callback")
def oauth_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    state = request.query_params.get("state", "")
    
    frontend_url = None
    is_login = False
    connect_user_id = None

    if state == 'login' or state.startswith('login:'):
        is_login = True
        if ':' in state:
            extracted = state.split(':', 1)[1]
            if extracted:
                frontend_url = extracted
    elif state.startswith('connect:'):
        parts = state.split(':')
        connect_user_id = parts[1]
        if len(parts) > 2 and parts[2]:
            frontend_url = parts[2]

    if not frontend_url:
        origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
        frontend_url = next((o for o in origins if "5174" in o), origins[0] if origins else "http://localhost:5174")
    
    frontend_url = frontend_url.rstrip("/")
    redirect_target = f"{frontend_url}/login" if is_login else f"{frontend_url}/automatic"

    if error:
        return RedirectResponse(url=f"{redirect_target}?error={error}")
    
    if not code:
        return RedirectResponse(url=f"{redirect_target}?error=no_code")

    try:
        flow = get_google_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Fast userinfo fetch - direct HTTP instead of building a discovery service
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=10
        )
        resp.raise_for_status()
        user_info = resp.json()
        email_address = user_info.get('email')
        full_name = user_info.get('name')

        # Store credentials securely
        creds_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': list(creds.scopes) if creds.scopes else list(SCOPES),
        }
        encrypted = encrypt_credential(json.dumps(creds_data))

        if is_login:
            # Find or create user for application access
            user = db.query(m.User).filter_by(email=email_address).first()
            if not user:
                base_username = email_address.split('@')[0].replace('.', '_').replace('-', '_')
                username = base_username
                counter = 1
                while db.query(m.User).filter_by(username=username).first():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                salt = secrets.token_hex(16)
                pwd = secrets.token_urlsafe(16)
                user = m.User(
                    username=username,
                    password_hash=hash_password(pwd, salt),
                    salt=salt,
                    full_name=full_name or username,
                    email=email_address,
                    role="analyst"
                )
                db.add(user)
                db.commit()
            
            owner_id = user.id
        elif connect_user_id:
            owner_id = connect_user_id
        else:
            owner_id = None

        # Update or create EmailAccount scoped to this user
        if owner_id:
            account = db.query(m.EmailAccount).filter_by(user_id=owner_id).first()
        else:
            account = db.query(m.EmailAccount).filter_by(email_address=email_address).first()
        
        if account:
            account.email_address = email_address
            account.provider = "gmail"
            account.auth_method = "oauth2"
            account.encrypted_credential = encrypted
            account.connected = True
            account.monitoring_active = True
        else:
            account = m.EmailAccount(
                user_id=owner_id,
                email_address=email_address, provider="gmail",
                auth_method="oauth2", encrypted_credential=encrypted, connected=True,
                monitoring_active=True
            )
            db.add(account)
        db.commit()

        # Start monitoring in background automatically
        email_monitor.start_monitoring(account.id, account.poll_interval_seconds)

        if is_login:
            # create session
            token = secrets.token_hex(32)
            _sessions[token] = user.id
            return RedirectResponse(url=f"{frontend_url}/login?token={token}")
        else:
            return RedirectResponse(url=f"{redirect_target}?connected=true")

    except Exception as e:
        import traceback
        print(f"OAUTH CALLBACK ERROR: {str(e)}")
        traceback.print_exc()
        return RedirectResponse(url=f"{redirect_target}?error=auth_failed")

@router.post("/disconnect")
def disconnect_email(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    account = db.query(m.EmailAccount).filter_by(user_id=user.id).first()
    if account:
        if account.monitoring_active:
            email_monitor.stop_monitoring(account.id)
        
        # Revoke token with Google if we have it
        try:
            from app.utils.crypto import decrypt_credential
            if account.encrypted_credential:
                creds_json = decrypt_credential(account.encrypted_credential)
                creds_data = json.loads(creds_json)
                token = creds_data.get('token')
                if token:
                    requests.post('https://oauth2.googleapis.com/revoke',
                                  params={'token': token},
                                  headers={'content-type': 'application/x-www-form-urlencoded'},
                                  timeout=5)
        except Exception:
            pass  # Ignore revoke errors

        account.connected = False
        account.monitoring_active = False
        account.encrypted_credential = None
        db.commit()
    return {"connected": False}


@router.post("/start-monitoring")
async def start_monitoring(payload: MonitoringIntervalRequest, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    account = db.query(m.EmailAccount).filter_by(user_id=user.id).first()
    if not account or not account.connected:
        raise HTTPException(status_code=400, detail="No connected email account. Connect one first.")
    account.poll_interval_seconds = payload.interval_seconds
    account.monitoring_active = True
    db.commit()
    email_monitor.start_monitoring(account.id, payload.interval_seconds)
    return {"monitoring_active": True}


@router.post("/stop-monitoring")
async def stop_monitoring(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    account = db.query(m.EmailAccount).filter_by(user_id=user.id).first()
    if account:
        account.monitoring_active = False
        db.commit()
        email_monitor.stop_monitoring(account.id)
    return {"monitoring_active": False}


@router.post("/sync-now")
async def sync_now(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    account = db.query(m.EmailAccount).filter_by(user_id=user.id).first()
    if not account or not account.connected:
        raise HTTPException(status_code=400, detail="No connected email account.")
    await email_monitor.sync_now(account.id)
    return {"status": "sync_complete"}
