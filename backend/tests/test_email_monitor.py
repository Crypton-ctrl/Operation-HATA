import sys
import asyncio
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from unittest.mock import patch, MagicMock
import base64
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.session import SessionLocal, Base, engine
from app.models import models as m
from app.services import email_monitor
from app.utils.crypto import encrypt_credential

Base.metadata.create_all(bind=engine)

async def test_email_monitor_pipeline():
    print("Testing Automated Email Monitoring Pipeline (OAuth2)...")
    db = SessionLocal()
    try:
        account = db.query(m.EmailAccount).first()
        creds_json = json.dumps({
            'token': 'test_token',
            'refresh_token': 'test_refresh',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
        })
        if not account:
            account = m.EmailAccount(
                email_address="soc-test@gmail.com",
                provider="gmail",
                auth_method="oauth2",
                encrypted_credential=encrypt_credential(creds_json),
                connected=True,
                monitoring_active=True
            )
            db.add(account)
            db.commit()
            db.refresh(account)
        else:
            account.connected = True
            account.encrypted_credential = encrypt_credential(creds_json)
            db.commit()

        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x00IEND\xae\x42\x60\x82"
        b64_png = base64.urlsafe_b64encode(png_bytes).decode('utf-8')

        mock_service = MagicMock()
        mock_messages = mock_service.users().messages()
        
        # Mock messages().list()
        mock_list_req = MagicMock()
        mock_list_req.execute.return_value = {'messages': [{'id': 'msg1'}]}
        mock_messages.list.return_value = mock_list_req
        
        # Mock messages().get()
        mock_get_req = MagicMock()
        mock_get_req.execute.return_value = {
            'id': 'msg1',
            'payload': {
                'headers': [
                    {'name': 'Message-ID', 'value': f'<test-{asyncio.get_event_loop().time()}@external.com>'},
                    {'name': 'From', 'value': 'suspicious-sender@external-domain.com'},
                    {'name': 'Subject', 'value': 'Urgent: Wire Transfer Invoice Attached'}
                ],
                'parts': [
                    {
                        'filename': 'invoice.png',
                        'mimeType': 'image/png',
                        'body': {'attachmentId': 'att1'}
                    }
                ]
            }
        }
        mock_messages.get.return_value = mock_get_req
        
        # Mock attachments().get()
        mock_att_req = MagicMock()
        mock_att_req.execute.return_value = {'data': b64_png}
        mock_messages.attachments().get.return_value = mock_att_req

        with patch("app.services.email_monitor.build", return_value=mock_service):
            with patch("app.services.email_monitor.Credentials"):
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
