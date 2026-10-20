# app/security/encryption.py  (MAI-PATCH security v1)
"""
Field-level encryption for sensitive data (Fernet, symmetric).

The key lives in <project root>/.encryption_key. It is created automatically the first time it is
needed -- importing this module no longer touches the disk.

Guarantees:
  * The key file is created atomically and is private (mode 600) from its very first byte.
  * Several threads or processes starting together all end up with the SAME key.
  * An unusable key file (empty, truncated, hand-edited) no longer stops the application from
    starting: it is moved aside as .encryption_key.corrupt-<time> -- never deleted -- and a new key is
    created. Values encrypted with the lost key can then no longer be read; the stored API key is simply
    regenerated (SQLiteMemoryManager.get reports it as "not set").
  * A key file that exists but cannot be READ (permissions, I/O error) is NOT replaced -- that could
    destroy a perfectly good key -- the problem is raised with an explanation instead.
  * An existing key file that other users can read is restricted to mode 600 (POSIX).

Back up .encryption_key together with memory/memory_store.db: the database alone is not enough to read
the encrypted values.

Inspect the key file without creating or printing anything:   python3 -m app.security.encryption
"""

import logging
import os
import stat
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
KEY_FILE_NAME = ".encryption_key"


class FieldEncryptor:
    """Handles encryption/decryption of sensitive fields."""

    def __init__(self, key_path: Optional[Path] = None):
        self.key_path = Path(key_path) if key_path else PROJECT_ROOT / KEY_FILE_NAME
        self._key: Optional[bytes] = None
        self._cipher: Optional[Fernet] = None
        self._lock = threading.Lock()

    # -- lazy initialisation ----------------------------------------------------------------
    def _ensure(self) -> Fernet:
        cipher = self._cipher
        if cipher is None:
            with self._lock:
                if self._cipher is None:
                    self._key = self._load_or_create_key(self.key_path)
                    self._cipher = Fernet(self._key)
                cipher = self._cipher
        return cipher

    @property
    def cipher(self) -> Fernet:
        return self._ensure()

    @property
    def key(self) -> bytes:
        self._ensure()
        return self._key  # type: ignore[return-value]

    # -- key file handling ------------------------------------------------------------------
    @staticmethod
    def _is_valid_key(key: bytes) -> bool:
        try:
            Fernet(key)
            return True
        except (ValueError, TypeError):
            return False

    def _load_or_create_key(self, key_path: Path) -> bytes:
        """Load the key, or create it. Never returns an unusable key; never destroys a readable one."""
        settled = False
        for _attempt in range(6):
            try:
                raw = key_path.read_bytes()
            except FileNotFoundError:
                raw = None
            except OSError as exc:
                raise RuntimeError(
                    f"Cannot read the encryption key file {key_path}: {exc}. The file was NOT replaced. "
                    "Fix its permissions or restore it from your backup, then restart."
                ) from exc

            if raw is not None:
                key = raw.strip()
                if self._is_valid_key(key):
                    self._restrict_permissions(key_path)
                    return key
                if not settled:
                    # Perhaps another process is writing it right now: look once more before judging.
                    settled = True
                    time.sleep(0.25)
                    continue
                self._quarantine(key_path)

            key = Fernet.generate_key()
            if self._create_exclusive(key_path, key):
                logger.info("Created a new encryption key at %s", key_path)
                return key
            # Another process created the file first: loop around and use theirs.
        raise RuntimeError(
            f"Could not create or read the encryption key file {key_path}"
        )

    @staticmethod
    def _quarantine(key_path: Path) -> None:
        target = key_path.with_name(
            f"{key_path.name}.corrupt-{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}"
        )
        try:
            os.replace(key_path, target)
        except FileNotFoundError:
            return  # another process already moved it
        except OSError as exc:
            raise RuntimeError(
                f"The encryption key file {key_path} is unusable and could not be moved aside: {exc}"
            ) from exc
        logger.error(
            "The encryption key file %s was unusable (empty, truncated or edited). It was moved to %s and a "
            "NEW key will be created. Anything encrypted with the old key -- e.g. the stored API key -- can "
            "no longer be read and will be regenerated. If you have a backup of the old file, restore it.",
            key_path,
            target.name,
        )

    @staticmethod
    def _create_exclusive(path: Path, key: bytes) -> bool:
        """Create `path` with `key`, only if it does not exist. True = we created it."""
        tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{threading.get_ident()}")
        try:
            fd = os.open(
                tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )  # private from the first byte
            with os.fdopen(fd, "wb") as handle:
                handle.write(key)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(
                    tmp, path
                )  # atomic "create if absent", with the complete content
                return True
            except FileExistsError:
                return False
            except OSError:
                # Filesystem without hard links (FAT, some network shares): exclusive create + write.
                try:
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    return False
                with os.fdopen(fd, "wb") as handle:
                    handle.write(key)
                    handle.flush()
                    os.fsync(handle.fileno())
                return True
        finally:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass

    @staticmethod
    def _restrict_permissions(path: Path) -> None:
        if os.name != "posix":
            return
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o077:
                os.chmod(path, 0o600)
                logger.warning(
                    "Encryption key file %s was readable by other users (mode %o); restricted it to 600.",
                    path,
                    mode,
                )
        except OSError as exc:
            logger.warning("Could not restrict permissions on %s: %s", path, exc)

    # -- public API -------------------------------------------------------------------------
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

    def describe(self) -> dict:
        """State of the key file. Never creates it and never returns the key itself."""
        info = {"path": str(self.key_path), "exists": False}
        try:
            status = self.key_path.stat()
            raw = self.key_path.read_bytes()
        except FileNotFoundError:
            return info
        except OSError as exc:
            info.update(exists=True, error=str(exc))
            return info
        info.update(
            exists=True,
            size_bytes=status.st_size,
            valid=self._is_valid_key(raw.strip()),
        )
        if os.name == "posix":
            mode = stat.S_IMODE(status.st_mode)
            info.update(mode=format(mode, "o"), private=not (mode & 0o077))
        return info


encryptor = FieldEncryptor()


if __name__ == "__main__":
    for _name, _value in encryptor.describe().items():
        print(f"  {_name:<11} {_value}")  # noqa: T201
    if not encryptor.key_path.exists():
        print(  # noqa: T201
            "\nNo key file yet: it is created the first time something sensitive is saved."
        )
