"""
Email Monitor
Connects to Gmail via Gmail API to detect new emails with image attachments.
Deduplicates using Message-ID and attachment SHA-256.
"""
import asyncio
import base64
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.database.session import SessionLocal
from app.models import models as m
from app.utils.crypto import decrypt_credential
from app.services.attachment_manager import save_bytes_to_quarantine, new_scan_id
from app.services.scan_orchestrator import run_full_scan
from app.services.ws_manager import manager

logger = logging.getLogger("hata.email_monitor")

_monitor_tasks: dict[str, asyncio.Task] = {}


def _get_settings_row(db: Session) -> m.UserSettings:
    row = db.query(m.UserSettings).filter_by(id="SETTINGS-DEFAULT").first()
    if not row:
        row = m.UserSettings(id="SETTINGS-DEFAULT")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row

def get_gmail_service(account: m.EmailAccount):
    if not account.encrypted_credential:
        return None
    try:
        creds_json = decrypt_credential(account.encrypted_credential)
        creds_data = json.loads(creds_json)
        creds = Credentials(**creds_data)
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to build gmail service: {e}")
        return None


import imaplib
import email as email_lib
from email.header import decode_header
from pathlib import Path
from app.utils.security import ALLOWED_EXTENSIONS

def _clean_header(val):
    if not val:
        return ""
    try:
        decoded_list = decode_header(val)
        parts = []
        for text, encoding in decoded_list:
            if isinstance(text, bytes):
                parts.append(text.decode(encoding or "utf-8", errors="ignore"))
            else:
                parts.append(str(text))
        return "".join(parts)
    except Exception:
        return str(val)

async def _poll_imap(account: m.EmailAccount, db: Session, settings_row: m.UserSettings):
    pwd = decrypt_credential(account.encrypted_credential)
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        mail.login(account.email_address, pwd)
        mail.select('INBOX')
        status, data = mail.search(None, 'UNSEEN')
        if status != 'OK' or not data or not data[0]:
            return
        
        msg_ids = data[0].split()[-25:]
        for msg_num in msg_ids:
            res, fetch_data = mail.fetch(msg_num, '(RFC822)')
            if res != 'OK' or not fetch_data:
                continue
            raw_email = fetch_data[0][1]
            msg = email_lib.message_from_bytes(raw_email)
            
            provider_message_id = msg.get('Message-ID') or f"imap-{msg_num.decode()}"
            existing = db.query(m.Email).filter_by(message_id=provider_message_id).first()
            if existing:
                continue

            sender = _clean_header(msg.get('From', 'Unknown'))
            subject = _clean_header(msg.get('Subject', 'No Subject'))

            email_row = m.Email(
                account_id=account.id, message_id=provider_message_id,
                sender=sender, subject=subject,
            )
            db.add(email_row)
            db.flush()
            account.emails_checked += 1
            image_found = False

            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                filename = part.get_filename()
                if not filename:
                    continue
                filename = _clean_header(filename)
                content_type = part.get_content_type() or ""
                ext = Path(filename).suffix.lower()

                is_image_mime = bool(content_type and content_type.startswith("image/"))
                is_image_ext = ext in ALLOWED_EXTENSIONS
                if not (is_image_mime or is_image_ext):
                    continue

                file_data = part.get_payload(decode=True)
                if not file_data:
                    continue

                scan_id = new_scan_id()
                saved = save_bytes_to_quarantine(file_data, filename, scan_id)
                if not saved:
                    continue

                image_found = True
                account.attachments_analyzed += 1

                attachment = m.Attachment(
                    email_id=email_row.id, original_filename=saved["original_filename"],
                    stored_filename=saved["stored_filename"], stored_path=saved["stored_path"],
                    content_type_declared=content_type, size_bytes=saved["size_bytes"],
                    source="automatic",
                    user_id=account.user_id,
                )
                db.add(attachment)
                db.flush()

                scan = m.Scan(
                    id=scan_id, attachment_id=attachment.id, source="automatic",
                    status="pending", user_id=account.user_id
                )
                db.add(scan)
                db.commit()

                await manager.broadcast("scan_started", {
                    "scan_id": scan.id, "source": "automatic",
                    "filename": attachment.original_filename, "sender": sender,
                })

                await run_full_scan(db, scan, Path(saved["stored_path"]), attachment, settings_row, email_row)

            email_row.has_image_attachments = image_found
            email_row.processed = True
            db.commit()

            try:
                mail.store(msg_num, '+FLAGS', '\\Seen')
            except Exception:
                pass

        account.last_sync_at = datetime.now()
        db.commit()
    finally:
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass

async def _poll_once(account_id: str):
    db = SessionLocal()
    try:
        account = db.query(m.EmailAccount).filter_by(id=account_id).first()
        if not account or not account.connected:
            return

        settings_row = _get_settings_row(db)

        if account.auth_method == "imap_app_password":
            await _poll_imap(account, db, settings_row)
            return

        service = get_gmail_service(account)
        if not service:
            return

        settings_row = _get_settings_row(db)

        # Get list of unread messages
        results = service.users().messages().list(userId='me', q="is:unread has:attachment").execute()
        messages = results.get('messages', [])

        for msg_ref in messages[:25]:
            msg_id = msg_ref['id']
            msg = service.users().messages().get(userId='me', id=msg_id).execute()
            
            headers = msg['payload'].get('headers', [])
            provider_message_id = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), msg_id)
            
            existing = db.query(m.Email).filter_by(message_id=provider_message_id).first()
            if existing:
                # Optional: mark as read if you want, but for now just skip
                continue

            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), "Unknown")
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "No Subject")

            email_row = m.Email(
                account_id=account.id, message_id=provider_message_id,
                sender=sender, subject=subject,
            )
            db.add(email_row)
            db.flush()
            
            account.emails_checked += 1
            image_found = False

            # Function to recursively find parts
            parts_to_process = []
            def extract_parts(parts):
                for part in parts:
                    if part.get('parts'):
                        extract_parts(part['parts'])
                    elif part.get('filename') and part.get('body', {}).get('attachmentId'):
                        parts_to_process.append(part)

            if 'parts' in msg['payload']:
                extract_parts(msg['payload']['parts'])
                
            from pathlib import Path
            from app.utils.security import ALLOWED_EXTENSIONS

            for part in parts_to_process:
                filename = part['filename']
                content_type = part.get('mimeType', '')
                ext = Path(filename).suffix.lower()
                
                is_image_mime = bool(content_type and content_type.startswith("image/"))
                is_image_ext = ext in ALLOWED_EXTENSIONS
                if not (is_image_mime or is_image_ext):
                    continue

                attachment_id = part['body']['attachmentId']
                attachment_obj = service.users().messages().attachments().get(
                    userId='me', messageId=msg_id, id=attachment_id
                ).execute()
                
                file_data = base64.urlsafe_b64decode(attachment_obj['data'])
                if not file_data:
                    continue

                scan_id = new_scan_id()
                saved = save_bytes_to_quarantine(file_data, filename, scan_id)
                if not saved:
                    continue

                image_found = True
                account.attachments_analyzed += 1

                attachment = m.Attachment(
                    email_id=email_row.id, original_filename=saved["original_filename"],
                    stored_filename=saved["stored_filename"], stored_path=saved["stored_path"],
                    content_type_declared=content_type, size_bytes=saved["size_bytes"],
                    source="automatic",
                    user_id=account.user_id,
                )
                db.add(attachment)
                db.flush()

                scan = m.Scan(
                    id=scan_id, attachment_id=attachment.id, source="automatic",
                    status="pending", user_id=account.user_id
                )
                db.add(scan)
                db.commit()

                await manager.broadcast("scan_started", {
                    "scan_id": scan.id, "source": "automatic",
                    "filename": attachment.original_filename, "sender": sender,
                })

                await run_full_scan(db, scan, Path(saved["stored_path"]), attachment, settings_row, email_row)

            email_row.has_image_attachments = image_found
            email_row.processed = True
            db.commit()

            # Mark message as read so we don't process it again (optional but good practice)
            try:
                service.users().messages().modify(
                    userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}
                ).execute()
            except Exception:
                pass

        account.last_sync_at = datetime.now()
        db.commit()

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
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_monitor_loop(account_id, interval_seconds))
        _monitor_tasks[account_id] = task
        return True
    except RuntimeError as err:
        logger.warning(f"Could not start monitor loop for {account_id}: {err}")
        return False


def stop_monitoring(account_id: str):
    task = _monitor_tasks.get(account_id)
    if task and not task.done():
        task.cancel()
        del _monitor_tasks[account_id]
        return True
    return False


async def sync_now(account_id: str):
    await _poll_once(account_id)
