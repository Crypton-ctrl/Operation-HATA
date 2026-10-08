"""
OCR Analysis
Extracts visible text from an image with Tesseract and flags supporting
indicators of social engineering / phishing content. A word like "urgent" or
"password" alone never classifies an image as malicious - these are only
supporting evidence combined with other findings.
"""
import re
from pathlib import Path
from app.config import get_settings

settings = get_settings()

try:
    import pytesseract
    from PIL import Image
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

SUSPICIOUS_PHRASES = [
    "verify your account", "urgent action required", "payment overdue",
    "invoice attached", "click here to", "confirm your password",
    "your account has been suspended", "wire transfer", "reset your password",
    "act now", "limited time", "bitcoin", "gift card", "irs", "tax refund",
    "security alert", "unusual activity", "update your billing",
]

URL_REGEX = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)


def analyze_ocr(file_path: Path) -> dict:
    if not OCR_AVAILABLE:
        return {
            "engine_available": False,
            "extracted_text": None,
            "suspicious_phrases": [],
            "urls_found": [],
        }

    try:
        with Image.open(file_path) as img:
            text = pytesseract.image_to_string(img)
    except Exception:
        return {
            "engine_available": False,
            "extracted_text": None,
            "suspicious_phrases": [],
            "urls_found": [],
        }

    text = (text or "").strip()
    lower = text.lower()

    found_phrases = [p for p in SUSPICIOUS_PHRASES if p in lower]
    urls = URL_REGEX.findall(text)

    return {
        "engine_available": True,
        "extracted_text": text if text else None,
        "suspicious_phrases": found_phrases,
        "urls_found": urls,
    }
