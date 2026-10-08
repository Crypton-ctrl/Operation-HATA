"""
Central configuration for Operation HATA.
Loads from environment variables / .env. No secrets are hardcoded.
"""
from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    SECRET_KEY: str = "insecure-dev-key-change-me"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173"

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/hata.db"

    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/api/emails/oauth/callback"

    IMAP_HOST: str = "imap.gmail.com"
    IMAP_PORT: int = 993

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
