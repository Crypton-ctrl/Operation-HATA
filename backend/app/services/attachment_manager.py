"""
Attachment Manager
Handles secure placement of uploaded/downloaded attachments into an isolated
per-scan quarantine directory. Files are never trusted by original name or
extension; generated filenames are used, path traversal is prevented, and
files are never overwritten.
"""
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import get_settings
from app.utils.security import (
    sanitize_filename, generate_stored_filename, is_within_directory,
    ALLOWED_EXTENSIONS, detect_image_format,
)

settings = get_settings()


def new_scan_id() -> str:
    return f"HATA-{uuid.uuid4().hex[:10].upper()}"


async def save_upload_to_quarantine(file: UploadFile, scan_id: str) -> dict:
    """Validates and stores an uploaded file. Raises HTTPException on validation failure."""
    original_name = sanitize_filename(file.filename or "upload")
    ext = Path(original_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=(
            f"Unsupported file extension '{ext}'. Supported formats: "
            f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
        ))

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=(
            f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_MB} MB."
        ))

    detected_format = detect_image_format(contents[:64])
    # Note: We do NOT reject files when detected_format is None.
    # Allowing disguised/polyglot files into quarantine is essential so that
    # the forensic signature engine can analyze and flag disguises (e.g. .exe disguised as .jpg).

    scan_dir = settings.QUARANTINE_DIR / scan_id
    scan_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = generate_stored_filename(original_name)
    stored_path = scan_dir / stored_filename

    if not is_within_directory(settings.QUARANTINE_DIR, stored_path):
        raise HTTPException(status_code=400, detail="Invalid file path.")

    # Never overwrite existing files
    counter = 0
    while stored_path.exists():
        counter += 1
        stored_filename = f"{Path(stored_filename).stem}_{counter}{Path(stored_filename).suffix}"
        stored_path = scan_dir / stored_filename

    with open(stored_path, "wb") as f:
        f.write(contents)

    return {
        "original_filename": original_name,
        "stored_filename": stored_filename,
        "stored_path": str(stored_path),
        "size_bytes": len(contents),
        "declared_mime": file.content_type,
        "detected_format": detected_format or "UNKNOWN",
    }


def save_bytes_to_quarantine(contents: bytes, original_name: str, scan_id: str) -> dict | None:
    """Used by the email monitor to place downloaded attachments into quarantine."""
    original_name = sanitize_filename(original_name)
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    detected_format = detect_image_format(contents[:64])
    if len(contents) > settings.max_upload_bytes:
        return None

    scan_dir = settings.QUARANTINE_DIR / scan_id
    scan_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = generate_stored_filename(original_name)
    stored_path = scan_dir / stored_filename

    if not is_within_directory(settings.QUARANTINE_DIR, stored_path):
        return None

    with open(stored_path, "wb") as f:
        f.write(contents)

    return {
        "original_filename": original_name,
        "stored_filename": stored_filename,
        "stored_path": str(stored_path),
        "size_bytes": len(contents),
        "declared_mime": None,
        "detected_format": detected_format,
    }
