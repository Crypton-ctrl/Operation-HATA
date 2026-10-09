"""
Demo Mode
Seeds the database with clearly-labeled SYNTHETIC scan records spanning
SAFE/LOW/MEDIUM/HIGH/CRITICAL so the dashboard can be demonstrated without a
connected Gmail account. No real malware is used or referenced; findings are
fabricated evidence dictionaries shaped exactly like real pipeline output.
"""
import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import models as m

DEMO_SENDERS = [
    "billing@vendor-support.com", "accounts@partner-invoices.net",
    "notifications@cloudsvc-alerts.com", "hr@internal-corp.com",
    "no-reply@shipping-updates.com",
]

DEMO_SCENARIOS = [
    {
        "filename": "team_photo.jpg", "category": "SAFE", "score": 8,
        "sig_status": "SAFE", "stego": "NOT DETECTED", "yara_matches": [],
        "embedded": [], "appended": False, "entropy_class": "NORMAL",
        "meta_anomaly": False, "ocr_phrases": [], "factors": [],
    },
    {
        "filename": "vacation_pic.png", "category": "LOW", "score": 28,
        "sig_status": "SAFE", "stego": "NOT DETECTED", "yara_matches": [],
        "embedded": [], "appended": False, "entropy_class": "ELEVATED",
        "meta_anomaly": True, "ocr_phrases": [],
        "factors": [{"factor": "Suspicious metadata", "points": 10, "reason": "Unusually large number of metadata fields present (68)."}],
    },
    {
        "filename": "scanned_document.jpg", "category": "MEDIUM", "score": 52,
        "sig_status": "SAFE", "stego": "POSSIBLE", "yara_matches": [],
        "embedded": [], "appended": False, "entropy_class": "ELEVATED",
        "meta_anomaly": False, "ocr_phrases": ["invoice attached", "wire transfer"],
        "factors": [
            {"factor": "Steganography indicator: POSSIBLE", "points": 5, "reason": "Statistical LSB/chi-square anomaly detected."},
            {"factor": "Social-engineering language detected via OCR", "points": 15, "reason": "Phrases found: invoice attached, wire transfer"},
        ],
    },
    {
        "filename": "payment_invoice.jpg", "category": "HIGH", "score": 78,
        "sig_status": "HIGH RISK", "stego": "NOT DETECTED", "yara_matches": [],
        "embedded": [{"type": "ZIP archive", "offset": 284921, "size": 43008, "severity": "MEDIUM"}],
        "appended": True, "entropy_class": "HIGH",
        "meta_anomaly": False, "ocr_phrases": ["urgent action required", "confirm your password"],
        "factors": [
            {"factor": "File signature mismatch", "points": 30, "reason": "Extension .jpg does not match detected content."},
            {"factor": "Embedded content (ZIP archive)", "points": 15, "reason": "Detected at offset 284921."},
            {"factor": "Social-engineering language detected via OCR", "points": 15, "reason": "Phrases found: urgent action required, confirm your password"},
        ],
    },
    {
        "filename": "shipping_label.png", "category": "CRITICAL", "score": 94,
        "sig_status": "HIGH RISK", "stego": "HIGHLY SUSPICIOUS",
        "yara_matches": [{"rule": "SuspiciousEmbeddedPayload", "description": "Detects script or shell interpreter markers concatenated with image data", "severity": "HIGH"}],
        "embedded": [{"type": "Windows PE executable (MZ)", "offset": 51204, "size": 102400, "severity": "CRITICAL"}],
        "appended": True, "entropy_class": "HIGH",
        "meta_anomaly": True, "ocr_phrases": ["urgent action required"],
        "factors": [
            {"factor": "File signature mismatch", "points": 30, "reason": "Extension .png does not match detected content."},
            {"factor": "Embedded executable (Windows PE executable (MZ))", "points": 40, "reason": "Detected at offset 51204."},
            {"factor": "YARA rule match: SuspiciousEmbeddedPayload", "points": 15, "reason": "Script/shell interpreter markers concatenated with image data."},
            {"factor": "Steganography indicator: HIGHLY SUSPICIOUS", "points": 25, "reason": "Statistical LSB/chi-square anomaly detected."},
        ],
    },
]


def seed_demo_data(db: Session, count_per_scenario: int = 2):
    created = 0
    run_tag = uuid.uuid4().hex[:8].upper()  # guarantees uniqueness across repeated seed calls
    for i in range(count_per_scenario):
        for idx, scenario in enumerate(DEMO_SCENARIOS):
            scan_id = f"HATA-DEMO-{run_tag}-{idx}{i}"
            sender = random.choice(DEMO_SENDERS)
            source = "automatic" if idx % 2 == 0 else "manual"

            email_row = None
            if source == "automatic":
                email_row = m.Email(
                    message_id=f"demo-{scan_id}@mail.example.com",
                    sender=sender, subject=f"[DEMO] Re: {scenario['filename']}",
                    received_at=datetime.now() - timedelta(hours=random.randint(1, 72)),
                    has_image_attachments=True, processed=True,
                )
                db.add(email_row)
                db.flush()

            attachment = m.Attachment(
                email_id=email_row.id if email_row else None,
                original_filename=scenario["filename"],
                stored_filename=f"demo_{scan_id}.bin",
                stored_path="DEMO/NOT_A_REAL_FILE",
                content_type_declared="image/jpeg",
                size_bytes=random.randint(50_000, 900_000),
                sha256=f"demo{scan_id.lower()}{'0'*40}"[:64],
                source=source,
            )
            db.add(attachment)
            db.flush()

            started = datetime.now() - timedelta(hours=random.randint(1, 96))
            scan = m.Scan(
                id=scan_id, attachment_id=attachment.id, source=source, status="complete",
                current_stage="complete", risk_score=scenario["score"], risk_category=scenario["category"],
                started_at=started, completed_at=started + timedelta(seconds=8),
            )
            db.add(scan)
            db.flush()

            db.add(m.SignatureResult(
                scan_id=scan.id, extension=f".{scenario['filename'].split('.')[-1]}",
                declared_mime="image/jpeg", detected_mime="image/jpeg",
                detected_format="JPEG" if scenario["sig_status"] == "SAFE" else "UNKNOWN",
                extension_mime_consistent=scenario["sig_status"] == "SAFE",
                status=scenario["sig_status"],
                details="[DEMO DATA] Synthetic signature analysis result.",
            ))
            db.add(m.FileHash(scan_id=scan.id, md5="demo", sha1="demo", sha256=attachment.sha256,
                               virustotal_status="not_configured"))
            db.add(m.MetadataResult(
                scan_id=scan.id, camera_make="Canon" if not scenario["meta_anomaly"] else None,
                software="Adobe Photoshop" if not scenario["meta_anomaly"] else "ExifTool 12.x",
                width=1920, height=1080, anomaly_detected=scenario["meta_anomaly"],
                anomalies=[{"finding": "[DEMO] Unusually large metadata field count", "severity": "low"}]
                if scenario["meta_anomaly"] else [],
            ))
            db.add(m.EntropyResult(
                scan_id=scan.id, overall_entropy=7.6 if scenario["entropy_class"] == "NORMAL" else 7.97,
                tail_entropy=7.5 if scenario["entropy_class"] == "NORMAL" else 7.95,
                classification=scenario["entropy_class"],
                anomaly_detected=scenario["entropy_class"] == "HIGH",
                chunk_entropies=[{"offset": j * 1000, "entropy": round(random.uniform(7.0, 8.0), 2)} for j in range(20)],
            ))
            db.add(m.SteganographyResult(
                scan_id=scan.id, classification=scenario["stego"],
                lsb_score=0.501 if scenario["stego"] != "NOT DETECTED" else 0.489,
                chi_square_score=3.1 if scenario["stego"] == "HIGHLY SUSPICIOUS" else 12.4,
                notes="[DEMO DATA] Synthetic steganography heuristic result.",
            ))
            db.add(m.EmbeddedContent(
                scan_id=scan.id, appended_data_found=scenario["appended"],
                appended_data_offset=scenario["embedded"][0]["offset"] if scenario["embedded"] else None,
                appended_data_size=scenario["embedded"][0]["size"] if scenario["embedded"] else None,
                embedded_signatures=scenario["embedded"],
                highest_severity=scenario["embedded"][0]["severity"] if scenario["embedded"] else "NONE",
            ))
            db.add(m.YaraResult(scan_id=scan.id, rules_scanned=24, matches=scenario["yara_matches"],
                                 engine_available=True))
            db.add(m.OcrResult(
                scan_id=scan.id, engine_available=True,
                extracted_text="[DEMO] " + " ".join(scenario["ocr_phrases"]) if scenario["ocr_phrases"] else None,
                suspicious_phrases=scenario["ocr_phrases"], urls_found=[],
            ))
            db.add(m.QrResult(scan_id=scan.id, engine_available=True, qr_codes=[]))
            db.add(m.RiskAssessment(
                scan_id=scan.id, total_score=scenario["score"], category=scenario["category"],
                contributing_factors=scenario["factors"],
            ))
            db.add(m.AiReport(
                scan_id=scan.id, ai_available=False,
                executive_summary=f"[DEMO DATA] Synthetic {scenario['category']}-risk scenario for demonstration purposes.",
                assessment="This is fabricated demo evidence, not a real scan result.",
                likely_scenario="N/A - demo record.",
                recommendation="No action needed - this record exists for UI demonstration only.",
                confidence="N/A", limitations="Synthetic demo data.",
            ))
            if scenario["category"] in ("MEDIUM", "HIGH", "CRITICAL"):
                db.add(m.QuarantineItem(
                    scan_id=scan.id, filename=attachment.original_filename, sha256=attachment.sha256,
                    risk_category=scenario["category"],
                    reason="[DEMO] " + (scenario["factors"][0]["factor"] if scenario["factors"] else "Elevated risk"),
                ))
            created += 1

    db.commit()
    return created
