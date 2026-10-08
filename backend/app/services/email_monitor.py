"""
Email Monitor
Connects to Gmail via IMAP (using an encrypted app-password credential) to
detect new emails with image attachments, deduplicates using the provider's
Message-ID header plus attachment SHA-256, downloads attachments into the
secure quarantine directory, and kicks off the standard analysis pipeline.

Gmail API/OAuth2 is the preferred integration per the architecture and the
credential storage model below already supports it (encrypted refresh
tokens) - swap `_fetch_via_imap` for a Gmail API client when OAuth
credentials are configured. This keeps the rest of the pipeline identical.
"""
import asyncio
import email
import imaplib
import logging
from datetime import datetime
from email.header import decode_header
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import SessionLocal
from app.models import models as m
from app.utils.crypto import decrypt_credential
from app.services.attachment_manager import save_bytes_to_quarantine, new_scan_id
from app.services.scan_orchestrator import run_full_scan
from app.services.ws_manager import manager

settings = get_settings()
logger = logging.getLogger("hata.email_monitor")

_monitor_tasks: dict[str, asyncio.Task] = {}


def _decode(value) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _get_settings_row(db: Session) -> m.UserSettings:
    row = db.query(m.UserSettings).filter_by(id="SETTINGS-DEFAULT").first()
    if not row:
        row = m.UserSettings(id="SETTINGS-DEFAULT")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


async def _poll_once(account_id: str):
    db = SessionLocal()
    try:
        account = db.query(m.EmailAccount).filter_by(id=account_id).first()
        if not account or not account.connected:
            return

        if not account.encrypted_credential:
            logger.warning("No credential stored for account %s", account_id)
            return

        try:
            app_password = decrypt_credential(account.encrypted_credential)
        except Exception:
            logger.error("Failed to decrypt credential for account %s", account_id)
            return

        try:
            imap = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
            imap.login(account.email_address, app_password)
            imap.select("INBOX")
        except Exception as exc:
            logger.error("IMAP connection failed: %s", exc)
            account.connected = False
            db.commit()
            return

        status, data = imap.search(None, "UNSEEN")
        message_ids = data[0].split() if status == "OK" else []

        settings_row = _get_settings_row(db)

        for msg_num in message_ids[-25:]:  # cap per poll cycle
            status, msg_data = imap.fetch(msg_num, "(RFC822)")
            if status != "OK":
                continue
            raw_email = msg_data[0][1]
            parsed = email.message_from_bytes(raw_email)

            provider_message_id = parsed.get("Message-ID", f"no-id-{msg_num}")
            existing = db.query(m.Email).filter_by(message_id=provider_message_id).first()
            if existing:
                continue  # already processed - dedup by Message-ID

            sender = _decode(parsed.get("From"))
            subject = _decode(parsed.get("Subject"))
            date_hdr = parsed.get("Date")

            email_row = m.Email(
                account_id=account.id, message_id=provider_message_id,
                sender=sender, subject=subject,
            )
            db.add(email_row)
            db.flush()

            account.emails_checked += 1
            image_found = False

            for part in parsed.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                filename = part.get_filename()
                if not filename:
                    continue
                filename = _decode(filename)
                content_type = part.get_content_type()
                from pathlib import Path
                from app.utils.security import ALLOWED_EXTENSIONS
                ext = Path(filename).suffix.lower()
                is_image_mime = bool(content_type and content_type.startswith("image/"))
                is_image_ext = ext in ALLOWED_EXTENSIONS
                if not (is_image_mime or is_image_ext):
                    continue

                payload = part.get_payload(decode=True)
                if not payload:
                    continue

                scan_id = new_scan_id()
                saved = save_bytes_to_quarantine(payload, filename, scan_id)
                if not saved:
                    continue

                image_found = True
                account.attachments_analyzed += 1

                attachment = m.Attachment(
                    email_id=email_row.id, original_filename=saved["original_filename"],
                    stored_filename=saved["stored_filename"], stored_path=saved["stored_path"],
                    content_type_declared=content_type, size_bytes=saved["size_bytes"],
                    source="automatic",
                )
                db.add(attachment)
                db.flush()

                scan = m.Scan(id=scan_id, attachment_id=attachment.id, source="automatic", status="pending")
                db.add(scan)
                db.commit()

                await manager.broadcast("scan_started", {
                    "scan_id": scan.id, "source": "automatic",
                    "filename": attachment.original_filename, "sender": sender,
                })

                from pathlib import Path
                await run_full_scan(db, scan, Path(saved["stored_path"]), attachment, settings_row, email_row)

            email_row.has_image_attachments = image_found
            email_row.processed = True
            db.commit()

        account.last_sync_at = datetime.utcnow()
        db.commit()
        imap.logout()

    except Exception as exc:  # noqa: BLE001
        logger.error("Email poll failed: %s", exc)
    finally:
        db.close()


async def _monitor_loop(account_id: str, interval_seconds: int):
    while True:
        await _poll_once(account_id)
        await asyncio.sleep(interval_seconds)


def start_monitoring(account_id: str, interval_seconds: int = 60):
    if account_id in _monitor_tasks and not _monitor_tasks[account_id].done():
        return False
    task = asyncio.create_task(_monitor_loop(account_id, interval_seconds))
    _monitor_tasks[account_id] = task
    return True


def stop_monitoring(account_id: str):
    task = _monitor_tasks.get(account_id)
    if task and not task.done():
        task.cancel()
        del _monitor_tasks[account_id]
        return True
    return False


async def sync_now(account_id: str):
    await _poll_once(account_id)
