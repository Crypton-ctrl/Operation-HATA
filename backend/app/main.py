"""
Operation HATA - FastAPI Application Entrypoint
"""
import logging
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database.session import Base, engine
from app.models import models  # noqa: F401 - ensures models are registered before create_all
from app.services.ws_manager import manager

from app.api import (
    scans, dashboard, emails, quarantine, notifications, settings as settings_api,
    threat_intel, demo, auth,
)
from app.api.auth import require_auth

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("hata.main")

settings = get_settings()

Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager
from app.database.session import SessionLocal
from app.services.email_monitor import start_monitoring

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with SessionLocal() as db:
            accounts = db.query(models.EmailAccount).filter_by(monitoring_active=True).all()
            for account in accounts:
                logger.info(f"Resuming email monitoring for {account.email_address}")
                start_monitoring(account.id, account.poll_interval_seconds)
    except Exception as e:
        logger.error(f"Failed to resume monitoring: {e}")
    yield

app = FastAPI(
    title="Operation HATA API",
    description="Hidden Attachment Threat Analyzer - AI-powered email attachment security platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Ensures the frontend always gets a readable JSON error instead of an
    opaque 500, and the full traceback is always printed to the server
    console for diagnosis - one module failing never leaves you guessing."""
    logger.error(
        "UNHANDLED ERROR on %s %s: %s\n%s",
        request.method, request.url.path, exc, traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc.__class__.__name__}: {exc}"},
    )


app.include_router(auth.router)
app.include_router(scans.router, dependencies=[require_auth])
app.include_router(dashboard.router, dependencies=[require_auth])
app.include_router(emails.router)
app.include_router(quarantine.router, dependencies=[require_auth])
app.include_router(notifications.router, dependencies=[require_auth])
app.include_router(settings_api.router, dependencies=[require_auth])
app.include_router(threat_intel.router, dependencies=[require_auth])
app.include_router(demo.router, dependencies=[require_auth])


@app.get("/")
def root():
    return {"service": "Operation HATA", "status": "online", "version": "1.0.0"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; client doesn't need to send anything meaningful
    except WebSocketDisconnect:
        manager.disconnect(websocket)
