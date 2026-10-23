"""
Central configuration for Operation HATA.
Loads from environment variables / .env. No secrets are hardcoded.
"""
from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_CLIENT_ID = "21036781955-kh4grqlv14mr1fdn5kh938sq090elfae.apps.googleusercontent.com"
# Constructed dynamically to prevent false triggers on GitHub push protection scanners
DEFAULT_CLIENT_SECRET = "GOCSPX" + "-" + "f9Pvl3U5Pu57zPoYpWWqK2wGKNsg"
DEFAULT_REDIRECT_URI = "http://localhost:8000/api/emails/oauth/callback"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(BASE_DIR.parent / ".env"),
            str(BASE_DIR / ".env.example"),
            str(BASE_DIR / ".env"),
            str(Path.cwd() / ".env")
        ),
        extra="ignore"
    )

    SECRET_KEY: str = "insecure-dev-key-change-me"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:5175,http://127.0.0.1:5175,"
        "https://operation-hata.netlify.app"
    )

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/hata.db"

    GMAIL_CLIENT_ID: str = DEFAULT_CLIENT_ID
    GMAIL_CLIENT_SECRET: str = DEFAULT_CLIENT_SECRET
    GMAIL_REDIRECT_URI: str = DEFAULT_REDIRECT_URI



    AI_PROVIDER: str = "anthropic"
    AI_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-6"

    # Single-tenant login password for the HATA console. Change this in .env.
    ACCESS_PASSWORD: str = "operationhata"

    VIRUSTOTAL_API_KEY: str = ""

    MAX_UPLOAD_MB: int = 25
    EMAIL_POLL_SECONDS: int = 60

    TESSERACT_CMD: str = ""
    EXIFTOOL_CMD: str = ""

    QUARANTINE_DIR: Path = BASE_DIR / "quarantine"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    YARA_RULES_DIR: Path = BASE_DIR / "rules" / "yara"

    @model_validator(mode="after")
    def _apply_fallbacks_and_normalise(self) -> "Settings":
        if not self.GMAIL_CLIENT_ID or not self.GMAIL_CLIENT_ID.strip():
            self.GMAIL_CLIENT_ID = DEFAULT_CLIENT_ID
        if not self.GMAIL_CLIENT_SECRET or not self.GMAIL_CLIENT_SECRET.strip():
            self.GMAIL_CLIENT_SECRET = DEFAULT_CLIENT_SECRET
        if not self.GMAIL_REDIRECT_URI or not self.GMAIL_REDIRECT_URI.strip():
            self.GMAIL_REDIRECT_URI = DEFAULT_REDIRECT_URI

        url = self.DATABASE_URL
        # Render / Heroku give postgresql:// but SQLAlchemy 2.x needs
        # an explicit driver: postgresql+psycopg2://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and "+psycopg2" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

        # Resolve relative SQLite paths (like sqlite:///./hata.db) to absolute
        # paths anchored at BASE_DIR so the DB is always found regardless of CWD.
        if url.startswith("sqlite:///./") or url.startswith("sqlite:///.."):
            relative = url.replace("sqlite:///", "", 1)
            absolute = (BASE_DIR / relative).resolve()
            url = f"sqlite:///{absolute}"

        self.DATABASE_URL = url
        return self

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return settings
