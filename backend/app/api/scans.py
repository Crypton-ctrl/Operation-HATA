"""
Scans API
Handles manual upload, starting analysis, retrieving results/history, and
generating downloadable PDF reports. Automatic (email-sourced) scans use the
identical underlying pipeline via app.services.scan_orchestrator.
"""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import models as m
from app.services.attachment_manager import save_upload_to_quarantine, new_scan_id
from app.services.scan_orchestrator import run_full_scan
from app.services.report_generator import generate_pdf_report
from app.utils.serializers import serialize_scan_summary, serialize_scan_full
from app.config import get_settings

router = APIRouter(prefix="/api/scans", tags=["scans"])
settings = get_settings()


def _get_settings_row(db: Session) -> m.UserSettings:
    row = db.query(m.UserSettings).filter_by(id="SETTINGS-DEFAULT").first()
    if not row:
        row = m.UserSettings(id="SETTINGS-DEFAULT")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.post("/upload")
async def upload_scan(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Validates and quarantines an uploaded image. Does NOT start analysis yet -
    call POST /api/scans/{id}/start to begin the pipeline."""
    scan_id = new_scan_id()
    saved = await save_upload_to_quarantine(file, scan_id)

    attachment = m.Attachment(
        original_filename=saved["original_filename"],
        stored_filename=saved["stored_filename"],
        stored_path=saved["stored_path"],
        content_type_declared=saved["declared_mime"],
        size_bytes=saved["size_bytes"],
        source="manual",
    )
    db.add(attachment)
    db.flush()

    scan = m.Scan(id=scan_id, attachment_id=attachment.id, source="manual", status="pending")
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return {
        "scan_id": scan.id,
        "filename": attachment.original_filename,
        "size_bytes": attachment.size_bytes,
        "detected_format": saved["detected_format"],
        "status": scan.status,
    }


@router.post("/{scan_id}/start")
async def start_scan(scan_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    scan = db.query(m.Scan).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if scan.status not in ("pending", "failed"):
        raise HTTPException(status_code=400, detail=f"Scan already {scan.status}.")

    attachment = scan.attachment
    file_path = Path(attachment.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=410, detail="Quarantined file no longer exists.")

    settings_row = _get_settings_row(db)
    email = attachment.email

    background_tasks.add_task(_run_scan_task, scan_id, file_path, attachment.id, settings_row.id, email.id if email else None)

    scan.status = "running"
    scan.current_stage = "file_received"
    db.commit()
    return {"scan_id": scan_id, "status": "running"}


def _run_scan_task(scan_id, file_path, attachment_id, settings_id, email_id):
    """Runs inside BackgroundTasks - needs its own DB session and event loop."""
    import asyncio
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        scan = db.query(m.Scan).filter_by(id=scan_id).first()
        attachment = db.query(m.Attachment).filter_by(id=attachment_id).first()
        settings_row = db.query(m.UserSettings).filter_by(id=settings_id).first()
        email = db.query(m.Email).filter_by(id=email_id).first() if email_id else None
        asyncio.run(run_full_scan(db, scan, Path(file_path), attachment, settings_row, email))
    finally:
        db.close()


@router.get("")
def list_scans(
    db: Session = Depends(get_db),
    source: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
):
    query = db.query(m.Scan)
    if source and source != "all":
        query = query.filter(m.Scan.source == source)
    if category and category != "all":
        query = query.filter(m.Scan.risk_category == category.upper())
    scans = query.order_by(m.Scan.started_at.desc()).limit(limit).all()
    results = [serialize_scan_summary(s) for s in scans]
    if search:
        s_lower = search.lower()
        results = [r for r in results if s_lower in (r.get("filename") or "").lower()
                   or s_lower in (r.get("sender") or "").lower()]
    return results


@router.get("/{scan_id}")
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(m.Scan).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return serialize_scan_full(scan)


@router.get("/{scan_id}/report")
def get_scan_report(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(m.Scan).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if scan.status != "complete":
        raise HTTPException(status_code=400, detail="Scan has not completed yet.")
    return serialize_scan_full(scan)


@router.get("/{scan_id}/report/pdf")
def download_pdf_report(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(m.Scan).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if scan.status != "complete":
        raise HTTPException(status_code=400, detail="Scan has not completed yet.")

    data = serialize_scan_full(scan)
    output_path = settings.REPORTS_DIR / f"{scan_id}.pdf"
    generate_pdf_report(data, output_path)
    return FileResponse(str(output_path), media_type="application/pdf",
                         filename=f"HATA_Report_{scan_id}.pdf")
