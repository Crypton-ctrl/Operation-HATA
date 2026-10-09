"""
Operation HATA - Database Models
All tables use string UUIDs as primary keys and store created_at timestamps.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from app.database.session import Base


def gen_id(prefix="HATA"):
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: gen_id("USER"))
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    email = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    role = Column(String, default="analyst")  # admin | analyst | hunter | auditor
    avatar = Column(String, default="shield")
    theme_preference = Column(String, default="cyber")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login_at = Column(DateTime, nullable=True)


class EmailAccount(Base):
    __tablename__ = "email_accounts"
    id = Column(String, primary_key=True, default=lambda: gen_id("ACC"))
    email_address = Column(String, nullable=False)
    provider = Column(String, default="gmail")
    auth_method = Column(String, default="oauth")  # oauth | imap_app_password
    # OAuth tokens or encrypted IMAP app password - never plaintext passwords
    encrypted_credential = Column(Text, nullable=True)
    connected = Column(Boolean, default=False)
    monitoring_active = Column(Boolean, default=False)
    poll_interval_seconds = Column(Integer, default=60)
    last_sync_at = Column(DateTime, nullable=True)
    emails_checked = Column(Integer, default=0)
    attachments_analyzed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    emails = relationship("Email", back_populates="account")


class Email(Base):
    __tablename__ = "emails"
    id = Column(String, primary_key=True, default=lambda: gen_id("EML"))
    account_id = Column(String, ForeignKey("email_accounts.id"), nullable=True)
    message_id = Column(String, unique=True, index=True)  # provider message id, dedup key
    sender = Column(String)
    subject = Column(String)
    received_at = Column(DateTime, default=datetime.now)
    has_image_attachments = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    account = relationship("EmailAccount", back_populates="emails")
    attachments = relationship("Attachment", back_populates="email")


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(String, primary_key=True, default=lambda: gen_id("ATT"))
    email_id = Column(String, ForeignKey("emails.id"), nullable=True)
    original_filename = Column(String)
    stored_filename = Column(String)
    stored_path = Column(String)
    content_type_declared = Column(String, nullable=True)
    size_bytes = Column(Integer)
    sha256 = Column(String, index=True)
    source = Column(String, default="manual")  # manual | automatic
    created_at = Column(DateTime, default=datetime.now)

    email = relationship("Email", back_populates="attachments")
    scan = relationship("Scan", back_populates="attachment", uselist=False)


class Scan(Base):
    __tablename__ = "scans"
    id = Column(String, primary_key=True, default=lambda: gen_id("SCAN"))
    attachment_id = Column(String, ForeignKey("attachments.id"))
    source = Column(String, default="manual")  # manual | automatic | demo
    status = Column(String, default="pending")  # pending|running|complete|failed
    current_stage = Column(String, default="queued")
    risk_score = Column(Integer, default=0)
    risk_category = Column(String, default="UNKNOWN")  # SAFE|LOW|MEDIUM|HIGH|CRITICAL
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    attachment = relationship("Attachment", back_populates="scan")
    file_hashes = relationship("FileHash", back_populates="scan", uselist=False)
    metadata_result = relationship("MetadataResult", back_populates="scan", uselist=False)
    entropy_result = relationship("EntropyResult", back_populates="scan", uselist=False)
    stego_result = relationship("SteganographyResult", back_populates="scan", uselist=False)
    embedded_content = relationship("EmbeddedContent", back_populates="scan", uselist=False)
    yara_result = relationship("YaraResult", back_populates="scan", uselist=False)
    ocr_result = relationship("OcrResult", back_populates="scan", uselist=False)
    qr_result = relationship("QrResult", back_populates="scan", uselist=False)
    url_results = relationship("UrlResult", back_populates="scan")
    ai_report = relationship("AiReport", back_populates="scan", uselist=False)
    risk_assessment = relationship("RiskAssessment", back_populates="scan", uselist=False)
    quarantine_item = relationship("QuarantineItem", back_populates="scan", uselist=False)
    signature_result = relationship("SignatureResult", back_populates="scan", uselist=False)


class SignatureResult(Base):
    __tablename__ = "signature_results"
    id = Column(String, primary_key=True, default=lambda: gen_id("SIG"))
    scan_id = Column(String, ForeignKey("scans.id"))
    extension = Column(String)
    declared_mime = Column(String, nullable=True)
    detected_mime = Column(String)
    detected_format = Column(String)
    extension_mime_consistent = Column(Boolean)
    status = Column(String)  # SAFE | HIGH RISK
    details = Column(Text, nullable=True)

    scan = relationship("Scan")


class FileHash(Base):
    __tablename__ = "file_hashes"
    id = Column(String, primary_key=True, default=lambda: gen_id("HASH"))
    scan_id = Column(String, ForeignKey("scans.id"))
    md5 = Column(String)
    sha1 = Column(String)
    sha256 = Column(String, index=True)
    virustotal_status = Column(String, default="not_configured")
    virustotal_result = Column(JSON, nullable=True)

    scan = relationship("Scan", back_populates="file_hashes")


class MetadataResult(Base):
    __tablename__ = "metadata_results"
    id = Column(String, primary_key=True, default=lambda: gen_id("META"))
    scan_id = Column(String, ForeignKey("scans.id"))
    camera_make = Column(String, nullable=True)
    camera_model = Column(String, nullable=True)
    software = Column(String, nullable=True)
    created_date = Column(String, nullable=True)
    modified_date = Column(String, nullable=True)
    gps_present = Column(Boolean, default=False)
    gps_data = Column(JSON, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    color_profile = Column(String, nullable=True)
    raw_exif = Column(JSON, nullable=True)
    anomalies = Column(JSON, default=list)  # list of {finding, severity}
    anomaly_detected = Column(Boolean, default=False)

    scan = relationship("Scan", back_populates="metadata_result")


class EntropyResult(Base):
    __tablename__ = "entropy_results"
    id = Column(String, primary_key=True, default=lambda: gen_id("ENT"))
    scan_id = Column(String, ForeignKey("scans.id"))
    overall_entropy = Column(Float)
    header_entropy = Column(Float, nullable=True)
    body_entropy = Column(Float, nullable=True)
    tail_entropy = Column(Float, nullable=True)
    chunk_entropies = Column(JSON, default=list)  # for chart visualization
    classification = Column(String)  # NORMAL | ELEVATED | HIGH
    anomaly_detected = Column(Boolean, default=False)

    scan = relationship("Scan", back_populates="entropy_result")


class SteganographyResult(Base):
    __tablename__ = "steganography_results"
    id = Column(String, primary_key=True, default=lambda: gen_id("STEGO"))
    scan_id = Column(String, ForeignKey("scans.id"))
    classification = Column(String)  # NOT DETECTED|POSSIBLE|SUSPICIOUS|HIGHLY SUSPICIOUS
    lsb_score = Column(Float, nullable=True)
    chi_square_score = Column(Float, nullable=True)
    indicators = Column(JSON, default=list)
    notes = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="stego_result")


class EmbeddedContent(Base):
    __tablename__ = "embedded_content"
    id = Column(String, primary_key=True, default=lambda: gen_id("EMB"))
    scan_id = Column(String, ForeignKey("scans.id"))
    appended_data_found = Column(Boolean, default=False)
    appended_data_offset = Column(Integer, nullable=True)
    appended_data_size = Column(Integer, nullable=True)
    embedded_signatures = Column(JSON, default=list)  # [{type, offset, size}]
    highest_severity = Column(String, default="NONE")

    scan = relationship("Scan", back_populates="embedded_content")


class YaraResult(Base):
    __tablename__ = "yara_results"
    id = Column(String, primary_key=True, default=lambda: gen_id("YARA"))
    scan_id = Column(String, ForeignKey("scans.id"))
    rules_scanned = Column(Integer, default=0)
    matches = Column(JSON, default=list)  # [{rule, description, severity}]
    engine_available = Column(Boolean, default=True)

    scan = relationship("Scan", back_populates="yara_result")


class OcrResult(Base):
    __tablename__ = "ocr_results"
    id = Column(String, primary_key=True, default=lambda: gen_id("OCR"))
    scan_id = Column(String, ForeignKey("scans.id"))
    engine_available = Column(Boolean, default=True)
    extracted_text = Column(Text, nullable=True)
    suspicious_phrases = Column(JSON, default=list)
    urls_found = Column(JSON, default=list)

    scan = relationship("Scan", back_populates="ocr_result")


class QrResult(Base):
    __tablename__ = "qr_results"
    id = Column(String, primary_key=True, default=lambda: gen_id("QR"))
    scan_id = Column(String, ForeignKey("scans.id"))
    engine_available = Column(Boolean, default=True)
    qr_codes = Column(JSON, default=list)  # [{content, type, risk}]

    scan = relationship("Scan", back_populates="qr_result")


class UrlResult(Base):
    __tablename__ = "url_results"
    id = Column(String, primary_key=True, default=lambda: gen_id("URL"))
    scan_id = Column(String, ForeignKey("scans.id"))
    url = Column(String)
    source = Column(String)  # ocr | qr
    is_https = Column(Boolean, default=False)
    is_ip_address = Column(Boolean, default=False)
    suspicious_tld = Column(Boolean, default=False)
    punycode = Column(Boolean, default=False)
    excessive_subdomains = Column(Boolean, default=False)
    suspicious_length = Column(Boolean, default=False)
    reputation_status = Column(String, default="not_configured")
    risk_level = Column(String, default="LOW")
    indicators = Column(JSON, default=list)

    scan = relationship("Scan", back_populates="url_results")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id = Column(String, primary_key=True, default=lambda: gen_id("RISK"))
    scan_id = Column(String, ForeignKey("scans.id"))
    total_score = Column(Integer)
    category = Column(String)
    contributing_factors = Column(JSON, default=list)  # [{factor, points, reason}]

    scan = relationship("Scan", back_populates="risk_assessment")


class AiReport(Base):
    __tablename__ = "ai_reports"
    id = Column(String, primary_key=True, default=lambda: gen_id("AI"))
    scan_id = Column(String, ForeignKey("scans.id"))
    ai_available = Column(Boolean, default=True)
    executive_summary = Column(Text, nullable=True)
    assessment = Column(Text, nullable=True)
    likely_scenario = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    confidence = Column(String, nullable=True)
    limitations = Column(Text, nullable=True)
    raw_model_output = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.now)

    scan = relationship("Scan", back_populates="ai_report")


class QuarantineItem(Base):
    __tablename__ = "quarantine_items"
    id = Column(String, primary_key=True, default=lambda: gen_id("QTN"))
    scan_id = Column(String, ForeignKey("scans.id"))
    filename = Column(String)
    sha256 = Column(String)
    risk_category = Column(String)
    reason = Column(Text, nullable=True)
    status = Column(String, default="quarantined")  # quarantined|deleted|restored
    created_at = Column(DateTime, default=datetime.now)
    resolved_at = Column(DateTime, nullable=True)

    scan = relationship("Scan", back_populates="quarantine_item")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=lambda: gen_id("NTF"))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    title = Column(String)
    message = Column(Text)
    severity = Column(String, default="info")  # info|low|medium|high|critical
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(String, primary_key=True, default=lambda: "SETTINGS-DEFAULT")
    max_upload_mb = Column(Integer, default=25)
    enabled_modules = Column(JSON, default=lambda: {
        "signature": True, "metadata": True, "entropy": True, "steganography": True,
        "embedded": True, "yara": True, "ocr": True, "qr": True, "url": True, "ai": True,
    })
    risk_thresholds = Column(JSON, default=lambda: {
        "SAFE": 20, "LOW": 40, "MEDIUM": 60, "HIGH": 80, "CRITICAL": 100
    })
    scoring_weights = Column(JSON, default=lambda: {
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
    })
    notifications_enabled = Column(Boolean, default=True)
    ai_provider = Column(String, default="anthropic")
    ai_model = Column(String, default="claude-sonnet-4-6")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
