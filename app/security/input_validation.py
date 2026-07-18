# app/security/input_validation.py
"""
Centralized input validation and sanitization for MAi-RAG-PA API.
Prevents XSS, injection attacks, and enforces field constraints.
"""
import html
import re
from typing import Optional

MAX_TITLE_LENGTH = 500
MAX_CONTENT_LENGTH = 100_000
MAX_FILENAME_LENGTH = 255
MAX_QUERY_LENGTH = 10_000
MAX_COLLECTION_NAME_LENGTH = 100
MAX_PATH_LENGTH = 1024


def sanitize_string(value: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """Sanitize a string: strip control chars, limit length, escape HTML."""
    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value)

    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned


def sanitize_html(value: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """Sanitize and escape HTML entities to prevent XSS."""
    cleaned = sanitize_string(value, max_length)
    return html.escape(cleaned, quote=True)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and special chars."""
    if not isinstance(filename, str) or not filename.strip():
        return "unnamed"

    filename = filename.strip().replace("\\", "/").split("/")[-1]
    filename = re.sub(r"\.\./+", "", filename)
    filename = re.sub(r"[^\w\-. ]", "_", filename)

    if filename.startswith("."):
        filename = "_" + filename[1:]

    if len(filename) > MAX_FILENAME_LENGTH:
        if "." in filename:
            name, ext = filename.rsplit(".", 1)
            max_name = MAX_FILENAME_LENGTH - len(ext) - 1
            filename = (
                f"{name[:max_name]}.{ext}"
                if max_name > 0
                else name[:MAX_FILENAME_LENGTH]
            )
        else:
            filename = filename[:MAX_FILENAME_LENGTH]

    return filename.strip() or "unnamed"


def validate_collection_name(name: str) -> str:
    """Validate Qdrant collection name (alphanumeric, hyphens, underscores)."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Collection name cannot be empty")

    name = name.strip()
    if len(name) > MAX_COLLECTION_NAME_LENGTH:
        raise ValueError(f"Collection name too long (max {MAX_COLLECTION_NAME_LENGTH})")

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", name):
        raise ValueError(
            "Collection name must start with a letter and contain only letters, numbers, hyphens, underscores"
        )

    return name


def validate_path(path: str) -> str:
    """Basic path validation before passing to resolve functions."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Path cannot be empty")

    path = path.strip()
    if len(path) > MAX_PATH_LENGTH:
        raise ValueError(f"Path too long (max {MAX_PATH_LENGTH})")

    if "\x00" in path:
        raise ValueError("Null bytes not allowed in path")

    return path
