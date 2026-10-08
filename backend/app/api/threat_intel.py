"""
Threat Intelligence API
Aggregates patterns across historical scans: repeated hashes, repeated
senders, common suspicious findings, and risk distribution. Works entirely
from local scan history - no external API is required.
"""
from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import models as m
from app.config import get_settings

router = APIRouter(prefix="/api/threat-intel", tags=["threat-intelligence"])
settings = get_settings()


@router.get("")
def threat_intelligence(db: Session = Depends(get_db)):
    scans = db.query(m.Scan).filter(m.Scan.status == "complete").all()

    threat_scans = [s for s in scans if s.risk_category in ("HIGH", "CRITICAL")]

    hash_counter = Counter()
    sender_counter = Counter()
    finding_counter = Counter()
    distribution = Counter(s.risk_category for s in scans)

    for s in scans:
        if s.file_hashes and s.file_hashes.sha256:
            hash_counter[s.file_hashes.sha256] += 1
        if s.attachment and s.attachment.email and s.attachment.email.sender:
            sender_counter[s.attachment.email.sender] += 1
        if s.risk_assessment:
            for f in (s.risk_assessment.contributing_factors or []):
                finding_counter[f["factor"]] += 1

    repeated_hashes = [{"sha256": h, "count": c} for h, c in hash_counter.items() if c > 1]
    repeated_senders = [{"sender": sname, "count": c} for sname, c in sender_counter.items() if c > 1]
    top_findings = [{"finding": f, "count": c} for f, c in finding_counter.most_common(10)]

    yara_rule_counter = Counter()
    for s in scans:
        if s.yara_result:
            for match in (s.yara_result.matches or []):
                yara_rule_counter[match.get("rule", "unknown")] += 1

    return {
        "total_threats_detected": len(threat_scans),
        "risk_distribution": dict(distribution),
        "top_findings": top_findings,
        "repeated_hashes": sorted(repeated_hashes, key=lambda x: -x["count"])[:10],
        "repeated_senders": sorted(repeated_senders, key=lambda x: -x["count"])[:10],
        "top_yara_rules": [{"rule": r, "count": c} for r, c in yara_rule_counter.most_common(10)],
        "virustotal_configured": bool(settings.VIRUSTOTAL_API_KEY),
    }
