"""
Security utilities: safe filenames, path traversal protection, size/type validation.
"""
import re
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"}

# Real magic-byte signatures for supported image formats
IMAGE_SIGNATURES = {
    "JPEG": [b"\xff\xd8\xff"],
    "PNG": [b"\x89PNG\r\n\x1a\n"],
    "GIF": [b"GIF87a", b"GIF89a"],
    "BMP": [b"BM"],
    "TIFF": [b"II*\x00", b"MM\x00*"],
    "WEBP": [b"RIFF"],  # further validated by "WEBP" at offset 8
}

EXT_TO_FORMAT = {
    ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".gif": "GIF",
    ".bmp": "BMP", ".tiff": "TIFF", ".tif": "TIFF", ".webp": "WEBP",
}


def sanitize_filename(filename: str) -> str:
    """Strip directory components and dangerous characters. Never trust client input."""
    name = Path(filename or "upload").name  # drop any path component (path traversal defense)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = name.lstrip(".")  # avoid hidden files / relative refs
    if not name:
        name = "upload"
    return name[:200]


def generate_stored_filename(original_filename: str) -> str:
    """Never trust the original filename for storage - generate a unique random name,
    but keep a normalized extension for downstream tooling that needs it."""
    ext = Path(sanitize_filename(original_filename)).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".bin"
    return f"{uuid.uuid4().hex}{ext}"


def is_within_directory(base_dir: Path, target: Path) -> bool:
    """Prevent path traversal - ensure target resolves inside base_dir."""
    try:
        base_resolved = base_dir.resolve()
        target_resolved = target.resolve()
        return str(target_resolved).startswith(str(base_resolved))
    except Exception:
        return False


def detect_image_format(file_bytes: bytes) -> str | None:
    """Detect actual image format from magic bytes, independent of extension."""
    if not file_bytes:
        return None
    for fmt, sigs in IMAGE_SIGNATURES.items():
        for sig in sigs:
            if file_bytes.startswith(sig):
                if fmt == "WEBP":
                    if len(file_bytes) >= 12 and file_bytes[8:12] == b"WEBP":
                        return "WEBP"
                    continue
                return fmt
    return None
