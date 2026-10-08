"""
Credential Encryption
Encrypts IMAP app-passwords / OAuth refresh tokens at rest using Fernet
symmetric encryption derived from SECRET_KEY. Plaintext credentials are never
written to the database.
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import get_settings

settings = get_settings()


def _fernet() -> Fernet:
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_credential(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_credential(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
