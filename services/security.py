from cryptography.fernet import Fernet
from config import settings
import logging

logger = logging.getLogger(__name__)

# Ensure FERNET_KEY is at least 32 url-safe base64 bytes
try:
    cipher_suite = Fernet(settings.FERNET_KEY.encode('utf-8'))
except Exception as e:
    logger.error(f"Failed to initialize Fernet cipher. Ensure FERNET_KEY is valid base64 32-byte string. Error: {e}")
    cipher_suite = None

def encrypt_token(token: str) -> bytes | None:
    if not token or not cipher_suite:
        return None
    return cipher_suite.encrypt(token.encode('utf-8'))

def decrypt_token(encrypted_token: bytes) -> str | None:
    if not encrypted_token or not cipher_suite:
        return None
    return cipher_suite.decrypt(encrypted_token).decode('utf-8')

