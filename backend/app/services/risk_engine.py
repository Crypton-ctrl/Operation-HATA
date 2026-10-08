"""
Risk Scoring Engine
Combines findings from every analysis module into a single 0-100 score with
a transparent, documented, configurable list of contributing factors.
Scoring is additive-with-caps: each factor contributes an explicitly bounded
amount, diminishing returns are applied to prevent unbounded stacking of
low-severity findings, and the final total is capped at 100.
"""

DEFAULT_WEIGHTS = {
    "signature_mismatch": 30,
    "embedded_executable": 40,
    "embedded_archive": 15,
    "appended_data": 20,
    "yara_high": 30,
    "yara_medium": 15,
    "yara_low": 5,
    "stego_highly_suspicious": 25,
    "stego_suspicious": 15,
    "stego_possible": 5,
    "metadata_anomaly_min": 5,
    "metadata_anomaly_max": 10,
    "qr_url_suspicious_min": 15,
    "qr_url_suspicious_max": 25,
    "ocr_suspicious_min": 5,
    "ocr_suspicious_max": 15,
    "entropy_high": 10,
}

CATEGORY_THRESHOLDS = [
    (20, "SAFE"),
    (40, "LOW"),
    (60, "MEDIUM"),
    (80, "HIGH"),
    (100, "CRITICAL"),
]


def categorize(score: int) -> str:
    for upper, label in CATEGORY_THRESHOLDS:
        if score <= upper:
            return label
    return "CRITICAL"


def calculate_risk(evidence: dict, weights: dict | None = None) -> dict:
    """
    evidence expects keys:
      signature: {status}
      embedded: {embedded_signatures: [...], appended_data_found}
      yara: {matches: [...]}
      stego: {classification}
      metadata: {anomaly_detected, anomalies}
      qr: {qr_codes: [...]}  (each may carry a 'url_analysis' sub-result)
      url_results: [ {risk_level, ...}, ... ]
      ocr: {suspicious_phrases}
      entropy: {classification}
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    factors = []
    total = 0

    # 1. Signature mismatch
    sig = evidence.get("signature") or {}
    if sig.get("status") == "HIGH RISK":
        pts = w["signature_mismatch"]
        total += pts
        factors.append({"factor": "File signature mismatch", "points": pts,
                         "reason": sig.get("details", "Extension/content mismatch detected.")})

    # 2. Embedded content
    embedded = evidence.get("embedded") or {}
    for sig_entry in embedded.get("embedded_signatures", []):
        sev = sig_entry.get("severity")
        if sev == "CRITICAL":
            pts = w["embedded_executable"]
            factors.append({"factor": f"Embedded executable ({sig_entry['type']})", "points": pts,
                             "reason": f"Detected at offset {sig_entry['offset']}."})
        elif sev in ("HIGH", "MEDIUM"):
            pts = w["embedded_archive"]
            factors.append({"factor": f"Embedded content ({sig_entry['type']})", "points": pts,
                             "reason": f"Detected at offset {sig_entry['offset']}."})
        else:
            continue
        total += pts

    if embedded.get("appended_data_found") and not embedded.get("embedded_signatures"):
        pts = w["appended_data"]
        total += pts
        factors.append({"factor": "Unidentified appended data after EOF", "points": pts,
                         "reason": f"{embedded.get('appended_data_size', 0)} bytes appended beyond expected end-of-file."})

    # 3. YARA matches
    yara = evidence.get("yara") or {}
    seen_sev = set()
    for match in yara.get("matches", []):
        sev = (match.get("severity") or "LOW").upper()
        key = f"yara_{sev.lower()}"
        weight_key = "yara_high" if sev in ("CRITICAL", "HIGH") else ("yara_medium" if sev == "MEDIUM" else "yara_low")
        if weight_key in seen_sev:
            continue  # avoid unbounded stacking of many similar-severity matches
        seen_sev.add(weight_key)
        pts = w[weight_key]
        total += pts
        factors.append({"factor": f"YARA rule match: {match.get('rule')}", "points": pts,
                         "reason": match.get("description", "")})

    # 4. Steganography
    stego = evidence.get("stego") or {}
    cls = stego.get("classification")
    if cls == "HIGHLY SUSPICIOUS":
        pts = w["stego_highly_suspicious"]
    elif cls == "SUSPICIOUS":
        pts = w["stego_suspicious"]
    elif cls == "POSSIBLE":
        pts = w["stego_possible"]
    else:
        pts = 0
    if pts:
        total += pts
        factors.append({"factor": f"Steganography indicator: {cls}", "points": pts,
                         "reason": "Statistical LSB/chi-square anomaly detected."})

    # 5. Metadata anomalies (scaled by count, capped)
    meta = evidence.get("metadata") or {}
    if meta.get("anomaly_detected"):
        count = len(meta.get("anomalies", []))
        pts = min(w["metadata_anomaly_min"] * max(count, 1), w["metadata_anomaly_max"])
        total += pts
        factors.append({"factor": "Suspicious metadata", "points": pts,
                         "reason": "; ".join(a["finding"] for a in meta.get("anomalies", [])[:3])})

    # 6. QR-embedded suspicious URLs
    for url_res in evidence.get("url_results", []):
        if url_res.get("source") != "qr":
            continue
        if url_res.get("risk_level") == "HIGH":
            pts = w["qr_url_suspicious_max"]
        elif url_res.get("risk_level") == "MEDIUM":
            pts = w["qr_url_suspicious_min"]
        else:
            continue
        total += pts
        factors.append({"factor": f"Suspicious QR-embedded URL ({url_res['url'][:60]})", "points": pts,
                         "reason": "; ".join(url_res.get("indicators", []))})
        break  # only count once to avoid stacking many similar QR URLs

    # 7. OCR social-engineering indicators
    ocr = evidence.get("ocr") or {}
    phrases = ocr.get("suspicious_phrases", [])
    if phrases:
        pts = min(w["ocr_suspicious_min"] * len(phrases), w["ocr_suspicious_max"])
        total += pts
        factors.append({"factor": "Social-engineering language detected via OCR", "points": pts,
                         "reason": f"Phrases found: {', '.join(phrases[:5])}"})

    # 8. Entropy
    entropy = evidence.get("entropy") or {}
    if entropy.get("classification") == "HIGH" and embedded.get("appended_data_found"):
        pts = w["entropy_high"]
        total += pts
        factors.append({"factor": "Elevated entropy in trailing data", "points": pts,
                         "reason": f"Tail entropy {entropy.get('tail_entropy')} bits/byte."})

    total = max(0, min(100, round(total)))
    category = categorize(total)

    return {
        "total_score": total,
        "category": category,
        "contributing_factors": factors,
    }
