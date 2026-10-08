"""
File Signature Analysis
Verifies actual file type via magic bytes rather than trusting the extension,
and flags extension/MIME/content mismatches as a significant security finding.
"""
from pathlib import Path
from app.utils.security import detect_image_format, EXT_TO_FORMAT


def analyze_signature(file_path: Path, original_filename: str, declared_mime: str | None) -> dict:
    with open(file_path, "rb") as f:
        header = f.read(64)

    detected_format = detect_image_format(header)
    extension = Path(original_filename).suffix.lower()
    expected_format = EXT_TO_FORMAT.get(extension)

    consistent = bool(detected_format) and detected_format == expected_format

    if detected_format is None:
        status = "HIGH RISK"
        details = (
            f"File extension '{extension or 'none'}' claims an image format, but no known "
            f"image signature was found in the file header. The file may be disguised, "
            f"corrupted, or not actually an image."
        )
    elif not consistent:
        status = "HIGH RISK"
        details = (
            f"Extension '{extension}' suggests {expected_format or 'an image'}, but the actual "
            f"file signature indicates {detected_format}. Extension/content mismatch is a "
            f"common technique used to disguise malicious files as images."
        )
    else:
        status = "SAFE"
        details = f"Extension '{extension}' is consistent with detected format {detected_format}."

    return {
        "extension": extension or "(none)",
        "declared_mime": declared_mime,
        "detected_mime": f"image/{detected_format.lower()}" if detected_format else "unknown",
        "detected_format": detected_format or "UNKNOWN",
        "extension_mime_consistent": consistent,
        "status": status,
        "details": details,
    }
