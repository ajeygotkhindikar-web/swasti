"""Encryption for separately-secured interview transcripts."""
import base64
import hashlib

from cryptography.fernet import Fernet

from ..config import get_settings


def _fernet() -> Fernet:
    key = get_settings().transcript_key
    if not key:
        # Development fallback derived from the JWT secret. Production must set
        # TRANSCRIPT_ENCRYPTION_KEY (Fernet.generate_key()) from a secrets manager.
        key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().jwt_secret.encode()).digest())
    return Fernet(key)


def encrypt(text: str) -> str:
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
