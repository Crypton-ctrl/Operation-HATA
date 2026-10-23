"""
Email Monitor
Connects to Gmail via Gmail API or IMAP to detect new emails with image attachments.
Deduplicates using Message-ID and attachment SHA-256.
Proactively handles token refreshes, inline/nested attachments, and resilient polling loops.
"""
import asyncio
import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build

from app.config import get_settings, DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET
from app.database.session import SessionLocal
from app.models import models as m
from app.utils.crypto import decrypt_credential, encrypt_credential
from app.utils.security import ALLOWED_EXTENSIONS
from app.services.attachment_manager import save_bytes_to_quarantine, new_scan_id
from app.services.scan_orchestrator import run_full_scan
from app.services.ws_manager import manager

import imaplib
import email as email_lib
from email.header import decode_header

logger = logging.getLogger("hata.email_monitor")
settings = get_settings()

_monitor_tasks: dict[str, asyncio.Task] = {}
_main_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    _main_loop = loop


def is_monitoring_running(account_id: str) -> bool:
    task = _monitor_tasks.get(account_id)
    return task is not None and not task.done()


def _get_settings_row(db: Session) -> m.UserSettings:
    row = db.query(m.UserSettings).filter_by(id="SETTINGS-DEFAULT").first()
    if not row:
        row = m.UserSettings(id="SETTINGS-DEFAULT")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_gmail_service(account: m.EmailAccount, db: Session | None = None):
    if not account.encrypted_credential:
        return None
    try:
        creds_json = decrypt_credential(account.encrypted_credential)
        creds_data = json.loads(creds_json)

        client_id = creds_data.get('client_id') or settings.GMAIL_CLIENT_ID or DEFAULT_CLIENT_ID
        client_secret = creds_data.get('client_secret') or settings.GMAIL_CLIENT_SECRET or DEFAULT_CLIENT_SECRET
        token_uri = creds_data.get('token_uri') or "https://oauth2.googleapis.com/token"

        creds = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=creds_data.get('scopes'),
        )

        # Proactively refresh token if expired
        if creds.expired and creds.refresh_token:
            logger.info(f"Access token expired for {account.email_address}, refreshing via Google OAuth...")
            try:
                creds.refresh(GoogleAuthRequest())
                creds_data['token'] = creds.token
                creds_data['client_id'] = client_id
                creds_data['client_secret'] = client_secret
                if db:
                    account.encrypted_credential = encrypt_credential(json.dumps(creds_data))
                    db.commit()
            except Exception as ref_err:
                logger.warning(f"Proactive token refresh error for {account.email_address}: {ref_err}")

        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error(f"Failed to build gmail service for {account.email_address}: {e}")
        return None


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
        return "".join(parts).strip().strip('"\'')
    except Exception:
        return str(val).strip().strip('"\'')


async def _poll_imap(account: m.EmailAccount, db: Session, settings_row: m.UserSettings):
    pwd = decrypt_credential(account.encrypted_credential)
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        mail.login(account.email_address, pwd)
        mail.select('INBOX')

        # Check for unseen messages first
        status, data = mail.search(None, 'UNSEEN')
        msg_ids = data[0].split() if (status == 'OK' and data and data[0]) else []

        # If no unseen messages found, inspect the latest 15 inbox messages so that
        # recently arrived/viewed test emails are not missed.
        if not msg_ids:
            status, all_data = mail.search(None, 'ALL')
            if status == 'OK' and all_data and all_data[0]:
                msg_ids = all_data[0].split()[-15:]
        else:
            msg_ids = msg_ids[-25:]

        for msg_num in msg_ids:
            res, fetch_data = mail.fetch(msg_num, '(RFC822)')
            if res != 'OK' or not fetch_data:
                continue
            raw_email = fetch_data[0][1]
            if not isinstance(raw_email, bytes):
                continue
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
                content_type = part.get_content_type() or ""

                # Handle inline or named images
                if not filename:
                    if content_type.startswith("image/"):
                        sub = content_type.split("/")[-1].lower()
                        sub = "jpg" if sub == "jpeg" else sub
                        filename = f"inline_image.{sub}"
                    else:
                        continue
                else:
                    filename = _clean_header(filename)

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

        service = get_gmail_service(account, db=db)
        if not service:
            logger.warning(f"Could not initialize Gmail service for account {account.email_address}")
            return

        settings_row = _get_settings_row(db)

        # Resilient query: fetch recent messages with attachments, image extensions, or unread
        query = "has:attachment OR filename:(png OR jpg OR jpeg OR gif OR bmp OR webp OR tif OR tiff) OR is:unread"
        try:
            results = service.users().messages().list(userId='me', maxResults=20, q=query).execute()
        except Exception as list_err:
            logger.warning(f"Query '{query}' failed ({list_err}), falling back to standard message list")
            results = service.users().messages().list(userId='me', maxResults=20).execute()

        messages = results.get('messages', [])
        logger.info(f"Gmail poll for {account.email_address}: found {len(messages)} candidate messages")

        for msg_ref in messages:
            msg_id = msg_ref['id']
            msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

            headers = msg.get('payload', {}).get('headers', [])
            provider_message_id = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), msg_id)

            existing = db.query(m.Email).filter_by(message_id=provider_message_id).first()
            if existing:
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

            # Recursively find all parts with image data (handles root payload, nested parts, and inline attachments)
            parts_to_process = []
            def extract_parts(part):
                if not isinstance(part, dict):
                    return
                sub_parts = part.get('parts')
                if sub_parts and isinstance(sub_parts, list):
                    for sp in sub_parts:
                        extract_parts(sp)

                filename = part.get('filename', '')
                mime_type = part.get('mimeType', '')
                body = part.get('body', {})
                has_data = bool(body.get('attachmentId') or body.get('data'))

                ext = Path(filename).suffix.lower() if filename else ''
                is_img = mime_type.startswith('image/') or ext in ALLOWED_EXTENSIONS
                if has_data and (filename or is_img):
                    if not filename and is_img:
                        sub = mime_type.split('/')[-1].lower() if '/' in mime_type else 'png'
                        sub = 'jpg' if sub == 'jpeg' else sub
                        part['filename'] = f"image_attachment.{sub}"
                    parts_to_process.append(part)

            extract_parts(msg.get('payload', {}))

            for part in parts_to_process:
                filename = part.get('filename', '')
                content_type = part.get('mimeType', '')
                ext = Path(filename).suffix.lower()

                is_image_mime = bool(content_type and content_type.startswith("image/"))
                is_image_ext = ext in ALLOWED_EXTENSIONS
                if not (is_image_mime or is_image_ext):
                    continue

                body = part.get('body', {})
                file_data = None
                attachment_id = body.get('attachmentId')
                if attachment_id:
                    try:
                        att_obj = service.users().messages().attachments().get(
                            userId='me', messageId=msg_id, id=attachment_id
                        ).execute()
                        raw_b64 = att_obj.get('data', '')
                        if raw_b64:
                            file_data = base64.urlsafe_b64decode(raw_b64)
                    except Exception as att_err:
                        logger.warning(f"Failed to fetch attachment {attachment_id}: {att_err}")
                elif body.get('data'):
                    try:
                        file_data = base64.urlsafe_b64decode(body['data'])
                    except Exception as att_err:
                        logger.warning(f"Failed to decode inline body data: {att_err}")

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

            # Attempt to mark message read if permitted by granted scopes
            try:
                service.users().messages().modify(
                    userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}
                ).execute()
            except Exception:
                pass

        account.last_sync_at = datetime.now()
        db.commit()

    except Exception as exc:  # noqa: BLE001
        logger.error(f"Email poll failed for account {account_id}: {exc}", exc_info=True)
        if "insufficientPermissions" in str(exc) or "insufficient authentication scopes" in str(exc).lower():
            logger.warning(f"Account {account_id} lacks Gmail API scope. Keeping connection alive but pausing monitoring.")
            try:
                if account:
                    account.monitoring_active = False
                    db.commit()
                stop_monitoring(account_id)
            except Exception:
                pass
    finally:
        db.close()


async def _monitor_loop(account_id: str, interval_seconds: int):
    logger.info(f"Monitor loop started for account {account_id} with interval {interval_seconds}s")
    while True:
        try:
            await _poll_once(account_id)
        except asyncio.CancelledError:
            logger.info(f"Monitor loop cancelled for account {account_id}")
            break
        except Exception as exc:
            logger.error(f"Error in monitor loop for account {account_id}: {exc}", exc_info=True)

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break


def start_monitoring(account_id: str, interval_seconds: int = 60):
    if account_id in _monitor_tasks and not _monitor_tasks[account_id].done():
        logger.info(f"Monitor loop already running for {account_id}")
        return True
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = _main_loop
        if not loop or loop.is_closed():
            logger.warning(f"Could not get active event loop to start monitoring for {account_id}")
            return False

        task = loop.create_task(_monitor_loop(account_id, interval_seconds))
        _monitor_tasks[account_id] = task
        logger.info(f"Successfully started monitor task for {account_id}")
        return True
    except Exception as err:
        logger.warning(f"Could not start monitor loop for {account_id}: {err}")
        return False


def stop_monitoring(account_id: str):
    task = _monitor_tasks.get(account_id)
    if task and not task.done():
        task.cancel()
        del _monitor_tasks[account_id]
        logger.info(f"Stopped monitor task for {account_id}")
        return True
    return False


async def sync_now(account_id: str):
    await _poll_once(account_id)
