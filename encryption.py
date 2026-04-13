"""Field-level encryption for sensitive data like Gmail refresh tokens."""

import os
import base64
import logging

logger = logging.getLogger(__name__)

# Use Fernet symmetric encryption
_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet

    key = os.environ.get("ENCRYPTION_KEY", "").strip()
    if not key:
        # Generate a key and warn — in production this should be set
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        logger.warning("ENCRYPTION_KEY not set. Generated temporary key. Set ENCRYPTION_KEY env var for persistence.")
        os.environ["ENCRYPTION_KEY"] = key

    try:
        from cryptography.fernet import Fernet
        # Key must be 32 url-safe base64-encoded bytes
        if len(key) != 44:
            # Hash the key to get a proper Fernet key
            import hashlib
            hashed = hashlib.sha256(key.encode()).digest()
            key = base64.urlsafe_b64encode(hashed).decode()
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        return _fernet
    except Exception as e:
        logger.error("Failed to initialize encryption: %s", e)
        return None


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    if not f:
        logger.warning("Encryption unavailable, storing plaintext")
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a string. Returns plaintext."""
    f = _get_fernet()
    if not f:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # Might be legacy unencrypted data
        logger.warning("Decryption failed, returning raw value (possible legacy data)")
        return ciphertext
