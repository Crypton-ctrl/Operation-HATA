"""
Multi-User Authentication API for Operation HATA
Supports individual user accounts with usernames and passwords, role-based profiles,
session management, and user preference persistence.
"""
import hashlib
import secrets
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db, SessionLocal
from app.models import models as m
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

# In-memory session store mapping active token -> user_id
_sessions: dict[str, str] = {}


def hash_password(password: str, salt: str) -> str:
    """PBKDF2 HMAC SHA-256 secure hash with 100,000 iterations."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()


def serialize_user(user: m.User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "email": user.email or "",
        "role": user.role or "analyst",
        "avatar": user.avatar or "shield",
        "theme_preference": user.theme_preference or "cyber",
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


def seed_default_users(db: Session):
    """Seed initial team accounts if database is fresh."""
    defaults = [
        ("admin", "Admin@12345", "Security Administrator", "admin@hata.soc", "admin", "shield", "netflix"),
        ("analyst", "Analyst@123", "SOC Analyst", "analyst@hata.soc", "analyst", "zap", "cyber"),
        ("hunter", "Hunter@123", "Threat Hunter", "hunter@hata.soc", "hunter", "eye", "matrix"),
    ]
    for username, pwd, name, email, role, avatar, theme in defaults:
        existing = db.query(m.User).filter_by(username=username).first()
        if not existing:
            salt = secrets.token_hex(16)
            user = m.User(
                username=username,
                password_hash=hash_password(pwd, salt),
                salt=salt,
                full_name=name,
                email=email,
                role=role,
                avatar=avatar,
                theme_preference=theme,
            )
            db.add(user)
    db.commit()


# Flag to track whether default users have been seeded in this process.
# Seeding at import-time was unreliable because this module is imported
# *before* Base.metadata.create_all() runs in main.py, so the users
# table may not exist yet.  We seed lazily on first request instead.
_seeded = False


def ensure_default_users(db: Session):
    """Seed default accounts on first use (after tables exist)."""
    global _seeded
    if _seeded:
        return
    try:
        seed_default_users(db)
        _seeded = True
    except Exception:
        pass


class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = "analyst"
    theme_preference: Optional[str] = "cyber"


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar: Optional[str] = None
    theme_preference: Optional[str] = None


def _extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> m.User:
    token = _extract_token(authorization)
    if not token or token not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    user_id = _sessions[token]
    user = db.query(m.User).filter_by(id=user_id).first()
    if not user:
        _sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="User account not found.")
    return user


def _check_auth(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    token = _extract_token(authorization)
    if not token or token not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    return True


require_auth = Depends(_check_auth)


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    ensure_default_users(db)
    
    username = (payload.username or "").strip().lower()
    password = payload.password

    # If no username was passed (legacy single password form), check against ACCESS_PASSWORD
    # or fallback to admin
    if not username:
        if secrets.compare_digest(password, settings.ACCESS_PASSWORD):
            admin_user = db.query(m.User).filter_by(username="admin").first()
            token = secrets.token_hex(32)
            _sessions[token] = admin_user.id
            return {"token": token, "user": serialize_user(admin_user)}
        raise HTTPException(status_code=401, detail="Please enter both username and password.")

    user = db.query(m.User).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    computed_hash = hash_password(password, user.salt)
    if not secrets.compare_digest(computed_hash, user.password_hash):
        # Fallback to ACCESS_PASSWORD for admin
        if user.username == "admin" and secrets.compare_digest(password, settings.ACCESS_PASSWORD):
            pass
        else:
            raise HTTPException(status_code=401, detail="Invalid username or password.")

    try:
        user.last_login_at = datetime.now()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during login: {str(e)}")

    token = secrets.token_hex(32)
    _sessions[token] = user.id
    return {"token": token, "user": serialize_user(user)}


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    ensure_default_users(db)

    username = payload.username.strip().lower()
    if not username.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Username may only contain letters, numbers, hyphens, and underscores.")

    existing = db.query(m.User).filter_by(username=username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Username '{username}' is already taken.")

    salt = secrets.token_hex(16)
    user = m.User(
        username=username,
        password_hash=hash_password(payload.password, salt),
        salt=salt,
        full_name=(payload.full_name or "").strip() or username.capitalize(),
        email=(payload.email or "").strip() or None,
        role=payload.role or "analyst",
        avatar="shield",
        theme_preference=payload.theme_preference or "cyber",
        last_login_at=datetime.now(),
    )
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create account: {str(e)}")

    token = secrets.token_hex(32)
    _sessions[token] = user.id
    return {"token": token, "user": serialize_user(user), "message": "Account created successfully."}


@router.get("/me")
def get_me(user: m.User = Depends(get_current_user)):
    return serialize_user(user)


@router.put("/me")
def update_me(payload: UpdateProfileRequest, user: m.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.email is not None:
        user.email = payload.email.strip()
    if payload.avatar is not None:
        user.avatar = payload.avatar
    if payload.theme_preference is not None:
        user.theme_preference = payload.theme_preference
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: bool = Depends(_check_auth)):
    users = db.query(m.User).order_by(m.User.created_at.asc()).all()
    return [serialize_user(u) for u in users]


class UpdateRoleRequest(BaseModel):
    role: str

@router.delete("/users/{user_id}")
def delete_user(user_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    token = _extract_token(authorization)
    if not token or token not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    
    current_user_id = _sessions[token]
    current_user = db.query(m.User).filter_by(id=current_user_id).first()
    
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can perform this action.")
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
        
    target = db.query(m.User).filter_by(id=user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
        
    db.delete(target)
    db.commit()
    return {"status": "deleted"}

@router.put("/users/{user_id}/role")
def update_user_role(user_id: str, payload: UpdateRoleRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    token = _extract_token(authorization)
    if not token or token not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    
    current_user_id = _sessions[token]
    current_user = db.query(m.User).filter_by(id=current_user_id).first()
    
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can perform this action.")
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot change your own role.")
        
    target = db.query(m.User).filter_by(id=user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
        
    target.role = payload.role
    db.commit()
    db.refresh(target)
    return serialize_user(target)

@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    token = _extract_token(authorization)
    if token:
        _sessions.pop(token, None)
    return {"status": "logged_out"}
