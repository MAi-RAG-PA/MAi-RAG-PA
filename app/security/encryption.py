# app/security/encryption.py
"""
Field-level encryption for sensitive data.
Uses Fernet symmetric encryption with auto-generated key.
"""
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent


class FieldEncryptor:
    """Handles encryption/decryption of sensitive fields."""

    def __init__(self):
        key_path = PROJECT_ROOT / ".encryption_key"
        self.key = self._load_or_create_key(key_path)
        self.cipher = Fernet(self.key)

    def _load_or_create_key(self, key_path: Path) -> bytes:
        """Load an existing key or create a new one."""
        if key_path.exists():
            key = key_path.read_bytes().strip()
            if not key:
                raise ValueError(f"Encryption key file is empty: {key_path}")
            return key

        key = Fernet.generate_key()
        key_path.write_bytes(key)

        try:
            os.chmod(key_path, 0o600)
        except Exception as e:
            logger.warning(
                "Could not set restrictive permissions on %s: %s", key_path, e
            )

        return key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string."""
        if plaintext is None:
            raise ValueError("plaintext cannot be None")
        return self.cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        if ciphertext is None:
            raise ValueError("ciphertext cannot be None")
        return self.cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


encryptor = FieldEncryptor()
