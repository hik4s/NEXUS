import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_api_secret() -> str:
    return "nx_live_" + secrets.token_urlsafe(32)


def generate_webhook_secret() -> str:
    return "whsec_" + secrets.token_urlsafe(32)


def webhook_signature(secret: str, payload: dict) -> str:
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def secret_fingerprint(secret: str) -> str:
    return hash_secret(secret)[:16]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
