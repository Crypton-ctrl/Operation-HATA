"""
Hash Analysis
Computes MD5, SHA-1, SHA-256 (primary identifier).
Optionally queries VirusTotal if an API key is configured - never required.
"""
import hashlib
import requests
from pathlib import Path
from app.config import get_settings

settings = get_settings()


def compute_hashes(file_path: Path) -> dict:
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    return {
        "md5": md5.hexdigest(),
        "sha1": sha1.hexdigest(),
        "sha256": sha256.hexdigest(),
    }


def check_virustotal_reputation(sha256: str) -> dict:
    """Optional external reputation lookup. Returns 'not_configured' status when no
    API key is present rather than breaking the scan."""
    if not settings.VIRUSTOTAL_API_KEY:
        return {"status": "not_configured", "result": None}
    try:
        resp = requests.get(
            f"https://www.virustotal.com/api/v3/files/{sha256}",
            headers={"x-apikey": settings.VIRUSTOTAL_API_KEY},
            timeout=10,
        )
        if resp.status_code == 404:
            return {"status": "unknown", "result": None}
        if resp.status_code != 200:
            return {"status": "error", "result": {"http_status": resp.status_code}}
        data = resp.json()
        stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        return {"status": "found", "result": stats}
    except Exception as exc:  # noqa: BLE001 - external service must never crash scan
        return {"status": "error", "result": {"error": str(exc)}}
