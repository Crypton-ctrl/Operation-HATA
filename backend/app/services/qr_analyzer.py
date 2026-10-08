"""
QR Code Analysis
Detects and decodes QR codes inside images using pyzbar/OpenCV. Classifies
decoded content (URL, email, phone, plain text). QR URLs are NEVER visited
automatically - they are only parsed and heuristically assessed.
"""
import re
from pathlib import Path

try:
    from pyzbar.pyzbar import decode as zbar_decode
    from PIL import Image
    QR_AVAILABLE = True
except Exception:
    QR_AVAILABLE = False

URL_RE = re.compile(r"^https?://", re.IGNORECASE)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^(tel:)?\+?[0-9\-\s()]{7,}$")


def _classify_content(content: str) -> str:
    if URL_RE.match(content):
        return "URL"
    if content.lower().startswith("mailto:") or EMAIL_RE.match(content):
        return "EMAIL"
    if PHONE_RE.match(content):
        return "PHONE"
    return "TEXT"


def _quick_risk(content: str, content_type: str) -> str:
    """A lightweight preliminary risk tag; full URL heuristics run separately
    via url_analyzer for URL-type content."""
    if content_type == "URL":
        lowered = content.lower()
        if re.match(r"^https?://\d{1,3}(\.\d{1,3}){3}", lowered):
            return "HIGH"
        if not lowered.startswith("https://"):
            return "MEDIUM"
        return "LOW"
    return "LOW"


def analyze_qr(file_path: Path) -> dict:
    if not QR_AVAILABLE:
        return {"engine_available": False, "qr_codes": []}

    try:
        with Image.open(file_path) as img:
            decoded = zbar_decode(img)
    except Exception:
        return {"engine_available": False, "qr_codes": []}

    results = []
    for d in decoded:
        try:
            content = d.data.decode("utf-8", errors="replace")
        except Exception:
            content = str(d.data)
        content_type = _classify_content(content)
        results.append({
            "content": content,
            "type": content_type,
            "risk": _quick_risk(content, content_type),
        })

    return {"engine_available": True, "qr_codes": results}
