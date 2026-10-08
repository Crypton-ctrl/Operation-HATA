"""
URL Analysis
Analyzes URLs discovered via OCR or QR codes WITHOUT ever visiting them.
Applies well-known heuristic indicators. Never claims a URL is malicious
based on heuristics alone - optionally augments with VirusTotal if configured.
"""
import re
from urllib.parse import urlparse
from app.config import get_settings
from app.services.hash_analyzer import requests  # reuse requests import

settings = get_settings()

SUSPICIOUS_TLDS = {"zip", "top", "xyz", "gq", "tk", "cf", "ml", "ga", "click", "work", "loan"}
IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _normalize(url: str) -> str:
    url = url.strip().rstrip(".,);]")
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "http://" + url
    return url


def analyze_url(raw_url: str, source: str = "ocr") -> dict:
    url = _normalize(raw_url)
    parsed = urlparse(url)
    host = parsed.hostname or ""

    indicators = []

    is_https = parsed.scheme == "https"
    if not is_https:
        indicators.append("Non-HTTPS scheme")

    is_ip = bool(IP_RE.match(host))
    if is_ip:
        indicators.append("Host is a raw IP address rather than a domain name")

    subdomain_count = max(0, host.count(".") - 1)
    excessive_subdomains = subdomain_count >= 3
    if excessive_subdomains:
        indicators.append(f"Excessive subdomains ({subdomain_count})")

    tld = host.split(".")[-1].lower() if "." in host else ""
    suspicious_tld = tld in SUSPICIOUS_TLDS
    if suspicious_tld:
        indicators.append(f"Uses a TLD commonly associated with abuse ('.{tld}')")

    punycode = "xn--" in host.lower()
    if punycode:
        indicators.append("Punycode/IDN encoding detected - may impersonate a legitimate domain")

    suspicious_length = len(url) > 120
    if suspicious_length:
        indicators.append("Unusually long URL")

    if "%" in url and url.count("%") > 3:
        indicators.append("Heavily percent-encoded URL")

    score_flags = sum([not is_https, is_ip, excessive_subdomains, suspicious_tld, punycode, suspicious_length])
    if score_flags >= 3:
        risk_level = "HIGH"
    elif score_flags >= 1:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    reputation_status = "not_configured"
    if settings.VIRUSTOTAL_API_KEY:
        try:
            import base64
            url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
            resp = requests.get(
                f"https://www.virustotal.com/api/v3/urls/{url_id}",
                headers={"x-apikey": settings.VIRUSTOTAL_API_KEY},
                timeout=10,
            )
            reputation_status = "found" if resp.status_code == 200 else "unknown"
        except Exception:
            reputation_status = "error"

    return {
        "url": url,
        "source": source,
        "is_https": is_https,
        "is_ip_address": is_ip,
        "suspicious_tld": suspicious_tld,
        "punycode": punycode,
        "excessive_subdomains": excessive_subdomains,
        "suspicious_length": suspicious_length,
        "reputation_status": reputation_status,
        "risk_level": risk_level,
        "indicators": indicators,
    }
