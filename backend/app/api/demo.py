from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models import models as m
from app.services.demo_seed import seed_demo_data

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    created = seed_demo_data(db)
    return {"status": "seeded", "records_created": created}


@router.delete("/clear")
def clear_demo(db: Session = Depends(get_db)):
    demo_scans = db.query(m.Scan).filter(m.Scan.id.like("HATA-DEMO%")).all()
    ids = [s.id for s in demo_scans]
    att_ids = [s.attachment_id for s in demo_scans]
    db.query(m.QuarantineItem).filter(m.QuarantineItem.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.AiReport).filter(m.AiReport.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.RiskAssessment).filter(m.RiskAssessment.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.QrResult).filter(m.QrResult.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.OcrResult).filter(m.OcrResult.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.YaraResult).filter(m.YaraResult.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.EmbeddedContent).filter(m.EmbeddedContent.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.SteganographyResult).filter(m.SteganographyResult.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.EntropyResult).filter(m.EntropyResult.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.MetadataResult).filter(m.MetadataResult.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.FileHash).filter(m.FileHash.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.SignatureResult).filter(m.SignatureResult.scan_id.in_(ids)).delete(synchronize_session=False)
    db.query(m.Scan).filter(m.Scan.id.in_(ids)).delete(synchronize_session=False)
    db.query(m.Attachment).filter(m.Attachment.id.in_(att_ids)).delete(synchronize_session=False)
    db.commit()
    return {"status": "cleared", "removed": len(ids)}
