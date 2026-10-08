import sys
import asyncio
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import SessionLocal, Base, engine
from app.models import models as m
from app.services import email_monitor
from app.utils.crypto import encrypt_credential

Base.metadata.create_all(bind=engine)

async def test_email_monitor_pipeline():
    print("Testing Automated Email Monitoring Pipeline...")
    db = SessionLocal()
    try:
        account = db.query(m.EmailAccount).first()
        if not account:
            account = m.EmailAccount(
                email_address="soc-test@gmail.com",
                provider="gmail",
                auth_method="imap_app_password",
                encrypted_credential=encrypt_credential("fake-app-password-16char"),
                connected=True,
                monitoring_active=True
            )
            db.add(account)
            db.commit()
            db.refresh(account)
        else:
            account.connected = True
            account.encrypted_credential = encrypt_credential("fake-app-password-16char")
            db.commit()

        msg = MIMEMultipart()
        msg["From"] = "suspicious-sender@external-domain.com"
        msg["To"] = "soc-test@gmail.com"
        msg["Subject"] = "Urgent: Wire Transfer Invoice Attached"
        msg["Message-ID"] = f"<test-{asyncio.get_event_loop().time()}@external-domain.com>"
        msg.attach(MIMEText("Please find the attached invoice.", "plain"))

        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x00IEND\xae\x42\x60\x82"
        img_part = MIMEImage(png_bytes, _subtype="png", name="invoice.png")
        img_part.add_header("Content-Disposition", "attachment", filename="invoice.png")
        msg.attach(img_part)

        raw_rfc822 = msg.as_bytes()

        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [b"Logged in"])
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b"1"])
        mock_imap.fetch.return_value = ("OK", [(b"1 (RFC822 {1234})", raw_rfc822)])
        mock_imap.logout.return_value = ("OK", [b"Logged out"])

        with patch("imaplib.IMAP4_SSL", return_value=mock_imap):
            await email_monitor._poll_once(account.id)

        scan = db.query(m.Scan).filter_by(source="automatic").order_by(m.Scan.started_at.desc()).first()
        assert scan is not None, "Scan should be created automatically by email monitor"
        assert scan.status in ("complete", "running"), f"Scan status: {scan.status}"
        assert scan.attachment is not None, "Attachment should be recorded"
        assert scan.attachment.original_filename == "invoice.png"
        print("  [SUCCESS] Automated Email Ingestion Succeeded!")
        print(f"  [SUCCESS] Scan ID: {scan.id}")
        print(f"  [SUCCESS] Sender: {scan.attachment.email.sender}")
        print(f"  [SUCCESS] Subject: {scan.attachment.email.subject}")
        print(f"  [SUCCESS] Attachment: {scan.attachment.original_filename} ({scan.attachment.size_bytes} bytes)")
        print(f"  [SUCCESS] Risk Score: {scan.risk_score} / Category: {scan.risk_category}")
        print(f"  [SUCCESS] Pipeline Status: {scan.status}")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_email_monitor_pipeline())
