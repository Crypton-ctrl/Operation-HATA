"""
Scan Orchestrator
Runs the full HATA analysis pipeline for a single attachment:
signature -> hash -> metadata -> entropy -> steganography -> embedded/appended
-> YARA -> OCR -> QR -> URL -> risk scoring -> AI interpretation -> persistence.

A failure in any individual module is caught and recorded as "unavailable" /
"failed" for that module only - it never aborts the rest of the pipeline
(per the spec's error-handling requirements).
"""
import logging
import traceback
from pathlib import Path
from sqlalchemy.orm import Session

from app.models import models as m
from app.services import (
    file_signature, hash_analyzer, metadata_analyzer, entropy_analyzer,
    stego_analyzer, embedded_file_analyzer, yara_scanner, ocr_analyzer,
    qr_analyzer, url_analyzer, risk_engine, ai_analyzer,
)
from app.services.ws_manager import manager

logger = logging.getLogger("hata.scan")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

STAGES = [
    "file_received", "signature_check", "hash_generation", "metadata_analysis",
    "entropy_analysis", "steganography_analysis", "embedded_data_analysis",
    "yara_scan", "ocr_analysis", "qr_analysis", "url_analysis",
    "risk_calculation", "ai_assessment", "complete",
]


async def _emit(scan_id: str, stage: str, status: str, extra: dict | None = None):
    payload = {"scan_id": scan_id, "stage": stage, "status": status}
    if extra:
        payload.update(extra)
    await manager.broadcast("scan_progress", payload)
    logger.info(f"scan_id={scan_id} STAGE={stage} STATUS={status}")


def _safe(fn, *args, module_name="module", **kwargs):
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:  # noqa: BLE001
        logger.error(f"{module_name} failed: {exc}\n{traceback.format_exc()}")
        return None, str(exc)


async def run_full_scan(db: Session, scan: m.Scan, file_path: Path, attachment: m.Attachment,
                         settings_obj: m.UserSettings, email: m.Email | None = None):
    scan.status = "running"
    db.commit()

    modules = settings_obj.enabled_modules or {}

    try:
        # --- Stage: signature ---
        await _emit(scan.id, "signature_check", "running")
        sig_result, err = _safe(
            file_signature.analyze_signature, file_path, attachment.original_filename,
            attachment.content_type_declared, module_name="signature"
        )
        sig_result = sig_result or {"status": "HIGH RISK", "extension": "-", "detected_format": "UNKNOWN",
                                     "detected_mime": "unknown", "extension_mime_consistent": False,
                                     "declared_mime": None, "details": f"Signature check failed: {err}"}
        db.add(m.SignatureResult(scan_id=scan.id, **sig_result))
        await _emit(scan.id, "signature_check", "complete")

        # --- Stage: hash ---
        await _emit(scan.id, "hash_generation", "running")
        hashes, _ = _safe(hash_analyzer.compute_hashes, file_path, module_name="hash")
        hashes = hashes or {"md5": "", "sha1": "", "sha256": ""}
        vt = {"status": "not_configured", "result": None}
        if hashes.get("sha256"):
            vt, _ = _safe(hash_analyzer.check_virustotal_reputation, hashes["sha256"], module_name="virustotal")
            vt = vt or {"status": "error", "result": None}
        attachment.sha256 = hashes.get("sha256")
        db.add(m.FileHash(scan_id=scan.id, md5=hashes.get("md5"), sha1=hashes.get("sha1"),
                           sha256=hashes.get("sha256"), virustotal_status=vt["status"],
                           virustotal_result=vt["result"]))
        await _emit(scan.id, "hash_generation", "complete")

        # --- Stage: metadata ---
        await _emit(scan.id, "metadata_analysis", "running")
        meta = {}
        if modules.get("metadata", True):
            meta, _ = _safe(metadata_analyzer.analyze_metadata, file_path, module_name="metadata")
        meta = meta or {"anomalies": [{"finding": "Metadata analysis failed", "severity": "info"}],
                         "anomaly_detected": False}
        db.add(m.MetadataResult(scan_id=scan.id, **{k: v for k, v in meta.items()}))
        await _emit(scan.id, "metadata_analysis", "complete")

        # --- Stage: entropy ---
        await _emit(scan.id, "entropy_analysis", "running")
        entropy = {}
        if modules.get("entropy", True):
            entropy, _ = _safe(entropy_analyzer.analyze_entropy, file_path, module_name="entropy")
        entropy = entropy or {"overall_entropy": 0, "classification": "NORMAL", "anomaly_detected": False,
                               "chunk_entropies": []}
        db.add(m.EntropyResult(scan_id=scan.id, **entropy))
        await _emit(scan.id, "entropy_analysis", "complete")

        # --- Stage: steganography ---
        await _emit(scan.id, "steganography_analysis", "running")
        stego = {}
        if modules.get("steganography", True):
            stego, _ = _safe(stego_analyzer.analyze_steganography, file_path, module_name="stego")
        stego = stego or {"classification": "NOT DETECTED", "indicators": [], "notes": "Stego module failed."}
        db.add(m.SteganographyResult(scan_id=scan.id, **stego))
        await _emit(scan.id, "steganography_analysis", "complete")

        # --- Stage: embedded/appended data ---
        await _emit(scan.id, "embedded_data_analysis", "running")
        embedded = {}
        if modules.get("embedded", True):
            embedded, _ = _safe(embedded_file_analyzer.analyze_embedded_content, file_path,
                                 sig_result.get("detected_format"), module_name="embedded")
        embedded = embedded or {"appended_data_found": False, "embedded_signatures": [], "highest_severity": "NONE"}
        db.add(m.EmbeddedContent(scan_id=scan.id, **embedded))
        await _emit(scan.id, "embedded_data_analysis", "complete")

        # --- Stage: YARA ---
        await _emit(scan.id, "yara_scan", "running")
        yara_res = {}
        if modules.get("yara", True):
            yara_res, _ = _safe(yara_scanner.scan_with_yara, file_path, module_name="yara")
        yara_res = yara_res or {"rules_scanned": 0, "matches": [], "engine_available": False}
        db.add(m.YaraResult(scan_id=scan.id, **yara_res))
        await _emit(scan.id, "yara_scan", "complete", {"matches": len(yara_res.get("matches", []))})

        # --- Stage: OCR ---
        await _emit(scan.id, "ocr_analysis", "running")
        ocr = {}
        if modules.get("ocr", True):
            ocr, _ = _safe(ocr_analyzer.analyze_ocr, file_path, module_name="ocr")
        ocr = ocr or {"engine_available": False, "extracted_text": None, "suspicious_phrases": [], "urls_found": []}
        db.add(m.OcrResult(scan_id=scan.id, **ocr))
        await _emit(scan.id, "ocr_analysis", "complete")

        # --- Stage: QR ---
        await _emit(scan.id, "qr_analysis", "running")
        qr = {}
        if modules.get("qr", True):
            qr, _ = _safe(qr_analyzer.analyze_qr, file_path, module_name="qr")
        qr = qr or {"engine_available": False, "qr_codes": []}
        db.add(m.QrResult(scan_id=scan.id, **qr))
        await _emit(scan.id, "qr_analysis", "complete")

        # --- Stage: URL analysis (from OCR + QR findings) ---
        await _emit(scan.id, "url_analysis", "running")
        url_result_rows = []
        if modules.get("url", True):
            for u in (ocr.get("urls_found") or [])[:5]:
                res, _ = _safe(url_analyzer.analyze_url, u, source="ocr", module_name="url")
                if res:
                    url_result_rows.append(res)
            for q in (qr.get("qr_codes") or []):
                if q.get("type") == "URL":
                    res, _ = _safe(url_analyzer.analyze_url, q["content"], source="qr", module_name="url")
                    if res:
                        url_result_rows.append(res)
        for res in url_result_rows:
            db.add(m.UrlResult(scan_id=scan.id, **res))
        await _emit(scan.id, "url_analysis", "complete", {"urls_found": len(url_result_rows)})

        db.commit()

        # --- Stage: risk calculation ---
        await _emit(scan.id, "risk_calculation", "running")
        evidence = {
            "signature": sig_result, "embedded": embedded, "yara": yara_res,
            "stego": stego, "metadata": meta, "url_results": url_result_rows,
            "ocr": ocr, "entropy": entropy,
        }
        risk = risk_engine.calculate_risk(evidence, weights=settings_obj.scoring_weights)
        db.add(m.RiskAssessment(scan_id=scan.id, **risk))
        scan.risk_score = risk["total_score"]
        scan.risk_category = risk["category"]
        await _emit(scan.id, "risk_calculation", "complete", {"score": risk["total_score"], "category": risk["category"]})

        # --- Stage: AI interpretation ---
        await _emit(scan.id, "ai_assessment", "running")
        ai_evidence = {
            "file_type": sig_result.get("detected_format"),
            "signature_valid": sig_result.get("extension_mime_consistent"),
            "metadata_anomaly": meta.get("anomaly_detected"),
            "entropy_anomaly": entropy.get("anomaly_detected"),
            "appended_data": embedded.get("appended_data_found"),
            "embedded_files": [e["type"] for e in embedded.get("embedded_signatures", [])],
            "yara_matches": [y["rule"] for y in yara_res.get("matches", [])],
            "ocr_findings": ocr.get("suspicious_phrases", []),
            "qr_findings": [q["content"][:60] for q in qr.get("qr_codes", [])],
            "steganography": stego.get("classification"),
            "hash_reputation": (hashes.get("sha256") and vt.get("status")) or "unknown",
            "risk_factors": risk["contributing_factors"],
        }
        ai_report, _ = _safe(ai_analyzer.generate_ai_report, ai_evidence, risk["total_score"],
                              risk["category"], module_name="ai")
        if not ai_report:
            ai_report = ai_analyzer._fallback_report(ai_evidence, risk["total_score"], risk["category"],
                                                       reason="AI module raised an exception")
        db.add(m.AiReport(scan_id=scan.id, **ai_report))
        await _emit(scan.id, "ai_assessment", "complete", {"ai_available": ai_report["ai_available"]})

        # --- Quarantine + notification for risky files ---
        if risk["category"] in ("MEDIUM", "HIGH", "CRITICAL"):
            db.add(m.QuarantineItem(
                scan_id=scan.id, filename=attachment.original_filename, sha256=hashes.get("sha256"),
                risk_category=risk["category"],
                reason="; ".join(f["factor"] for f in risk["contributing_factors"][:4]) or "Elevated risk score",
            ))
            severity = "critical" if risk["category"] == "CRITICAL" else ("high" if risk["category"] == "HIGH" else "medium")
            notif = m.Notification(
                scan_id=scan.id,
                title=f"{'CRITICAL THREAT' if risk['category']=='CRITICAL' else risk['category']+'-RISK ATTACHMENT'} DETECTED",
                message=f"{attachment.original_filename} - Risk: {risk['total_score']}/100",
                severity=severity,
            )
            db.add(notif)
            await manager.broadcast("notification", {
                "title": notif.title, "message": notif.message, "severity": severity, "scan_id": scan.id,
            })

        scan.status = "complete"
        scan.current_stage = "complete"
        from datetime import datetime
        scan.completed_at = datetime.utcnow()
        db.commit()
        await _emit(scan.id, "complete", "complete", {"score": risk["total_score"], "category": risk["category"]})
        await manager.broadcast("dashboard_update", {"scan_id": scan.id})

    except Exception as exc:  # noqa: BLE001 - top-level safety net
        logger.error(f"Scan {scan.id} failed catastrophically: {exc}\n{traceback.format_exc()}")
        scan.status = "failed"
        scan.error_message = str(exc)
        db.commit()
        await _emit(scan.id, "failed", "failed", {"error": str(exc)})
