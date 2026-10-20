# app/config.py  (MAI-PATCH config.py v1)
"""
Central settings for MAi-RAG-PA.

Where a value comes from (highest priority first):
  1. a real environment variable      export MAI_RAG_TOP_K=8
  2. the project's .env file          <project root>/.env   (plain KEY=VALUE lines)
  3. the default written below

A value that cannot be used (not a number, out of range, malformed URL, ...) never stops the
application from starting: it is reported on stderr as a WARNING and the default is used instead.

See what is in effect right now:      python3 -m app.config

.env syntax: KEY=VALUE, optional leading "export ", '#' comments, values may be wrapped in single
or double quotes. There is no variable expansion and no backslash escapes.
"""

import logging
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

_log = logging.getLogger("app.config")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

_WARNINGS: List[str] = []  # everything that was wrong with the configuration
_DOTENV_KEYS = set()  # variable names that were taken from the .env file
_REJECTED = (
    set()
)  # variable names whose value was unusable (the default was used instead)


def _warn(message: str) -> None:
    _WARNINGS.append(message)
    _log.warning(message)


# ---------------------------------------------------------------------------------------
# .env loading (real environment variables always win)
# ---------------------------------------------------------------------------------------
_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


def _parse_env_value(raw: str) -> str:
    raw = raw.strip()
    if raw[:1] in ("'", '"'):
        end = raw.find(raw[0], 1)
        if end != -1:
            return raw[1:end]  # quoted: everything between the quotes
    comment = re.search(r"\s#", raw)  # unquoted: " #..." starts a comment
    return (raw[: comment.start()] if comment else raw).strip()


def _load_env_file(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8-sig")  # tolerates a BOM
    except FileNotFoundError:
        return
    except (OSError, UnicodeDecodeError) as exc:
        _warn(f"Could not read {path.name}: {exc}")
        return
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if not match:
            _warn(
                f"{path.name} line {number}: ignored (expected KEY=VALUE)"
            )  # never echo the line: it may hold a secret
            continue
        key, value = match.group(1), _parse_env_value(match.group(2))
        if key not in os.environ:
            os.environ[key] = value
            _DOTENV_KEYS.add(key)


try:
    _load_env_file(ENV_FILE)
except Exception as exc:  # configuration must never be the reason startup fails
    _warn(f"Unexpected error while reading {ENV_FILE.name}: {exc}")


# ---------------------------------------------------------------------------------------
# Typed readers: bad input -> warning + default, never an exception
# ---------------------------------------------------------------------------------------
def _first_env(names) -> Tuple[Optional[str], Optional[str]]:
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip():
            return name, value.strip()
    return None, None


def _int_setting(names, default: int, minimum: int, maximum: int) -> int:
    name, raw = _first_env(names)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        _REJECTED.add(name)
        _warn(f"{name}={raw!r} is not a whole number; using the default ({default})")
        return default
    if not minimum <= value <= maximum:
        _REJECTED.add(name)
        _warn(
            f"{name}={value} is outside the allowed range {minimum}..{maximum}; using the default ({default})"
        )
        return default
    return value


def _text_setting(names, default: str) -> str:
    _name, raw = _first_env(names)
    return raw if raw is not None else default


def _url_setting(names, default: str) -> str:
    """An http(s) base URL. A missing scheme is added; a trailing '/' is removed; 'localhost' -> 127.0.0.1."""
    name, raw = _first_env(names)
    if raw is None:
        return default
    candidate = raw if "://" in raw else "http://" + raw
    try:
        parts = urlparse(candidate)
        port = parts.port  # raises ValueError for a bad port
        valid = parts.scheme in ("http", "https") and bool(parts.hostname)
    except ValueError:
        valid = False
    if not valid:  # (the value is not echoed: URLs can carry credentials)
        _REJECTED.add(name)
        _warn(f"{name} is not a valid http(s) URL; using the default ({default})")
        return default
    if parts.hostname == "localhost":
        # Ollama and Qdrant listen on the IPv4 loopback; "localhost" may resolve to ::1 first.
        # (start.sh exports OLLAMA_URL=http://localhost:11434.)
        userinfo = parts.netloc.rpartition("@")[0]
        netloc = (
            (userinfo + "@" if userinfo else "")
            + "127.0.0.1"
            + (f":{port}" if port else "")
        )
        candidate = urlunparse(parts._replace(netloc=netloc))
    return candidate.rstrip("/")


# Same grammar as the `limits` library that slowapi uses: "30/minute", "5 per 2 minutes", "100/hour;1000/day"
_RATE_ONE = re.compile(
    r"\s*([0-9]+)\s*(/|\s*per\s*)\s*([0-9]+)?\s*(hour|minute|second|day|month|year)s?\s*",
    re.IGNORECASE,
)
_RATE_SEP = re.compile(r"[,;|]")


def _rate_setting(name: str, default: str) -> str:
    _name, raw = _first_env((name,))
    if raw is None:
        return default
    parts = [_RATE_ONE.fullmatch(part) for part in _RATE_SEP.split(raw)]
    if all(parts) and all(int(m.group(1)) >= 1 for m in parts):
        return raw
    _REJECTED.add(name)
    _warn(
        f"{name}={raw!r} is not a valid rate limit (examples: '30/minute', '5 per 2 minutes'); using the default ({default!r})"
    )
    return default


# ---------------------------------------------------------------------------------------
# The settings
# ---------------------------------------------------------------------------------------
_NAMES = {
    "CONTEXT_WINDOW": ("MAI_CONTEXT_WINDOW",),
    "RAG_TOP_K": ("MAI_RAG_TOP_K",),
    "EMBEDDING_MODEL": ("MAI_EMBEDDING_MODEL",),
    "EMBEDDING_DIM": ("MAI_EMBEDDING_DIM",),
    "OLLAMA_URL": (
        "MAI_OLLAMA_URL",
        "OLLAMA_URL",
    ),  # OLLAMA_URL: what start.sh / first_launch.py / the docs use
    "QDRANT_URL": ("MAI_QDRANT_URL", "QDRANT_URL"),
    "BATCH_SIZE": ("MAI_BATCH_SIZE",),
    "RATE_LIMIT_CHAT": ("MAI_RATE_LIMIT_CHAT",),
    "RATE_LIMIT_INGEST": ("MAI_RATE_LIMIT_INGEST",),
}


class Config:
    # LLM & RAG settings
    CONTEXT_WINDOW = _int_setting(_NAMES["CONTEXT_WINDOW"], 8192, 512, 262144)
    RAG_TOP_K = _int_setting(_NAMES["RAG_TOP_K"], 5, 1, 100)

    # Embeddings used by app/rag/rag_core.py (Ollama)
    EMBEDDING_MODEL = _text_setting(
        _NAMES["EMBEDDING_MODEL"], "nomic-embed-text:latest"
    )
    EMBEDDING_DIM = _int_setting(_NAMES["EMBEDDING_DIM"], 768, 1, 8192)

    # Services (base URLs, no trailing slash)
    OLLAMA_URL = _url_setting(_NAMES["OLLAMA_URL"], "http://127.0.0.1:11434")
    QDRANT_URL = _url_setting(_NAMES["QDRANT_URL"], "http://127.0.0.1:6333")

    # Ingestion
    BATCH_SIZE = _int_setting(_NAMES["BATCH_SIZE"], 64, 1, 1024)

    # Rate limiting (slowapi syntax)
    RATE_LIMIT_CHAT = _rate_setting("MAI_RATE_LIMIT_CHAT", "30/minute")
    RATE_LIMIT_INGEST = _rate_setting("MAI_RATE_LIMIT_INGEST", "5/minute")

    @classmethod
    def describe(cls) -> List[Tuple[str, object, str]]:
        """(setting, effective value, where it came from) for every managed setting."""
        rows = []
        for attr, names in _NAMES.items():
            name, _raw = _first_env(names)
            if name is None:
                source = "default"
            else:
                origin = ".env" if name in _DOTENV_KEYS else "environment"
                source = (
                    f"default  (the value in {origin} was rejected)"
                    if name in _REJECTED
                    else origin
                )
            rows.append((attr, getattr(cls, attr), source))
        return rows


# Changing the embedding model without telling us its vector size is a classic silent failure:
# the collection is created with the wrong dimension and every upsert is rejected.
if (
    Config.EMBEDDING_MODEL != "nomic-embed-text:latest"
    and _first_env(_NAMES["EMBEDDING_DIM"])[0] is None
):
    _warn(
        f"MAI_EMBEDDING_MODEL is set to {Config.EMBEDDING_MODEL!r} but MAI_EMBEDDING_DIM is not: "
        f"assuming {Config.EMBEDDING_DIM}. Set MAI_EMBEDDING_DIM to your model's output size."
    )


if __name__ == "__main__":
    print(  # noqa: T201
        f"Settings file: {ENV_FILE}  ({'found' if ENV_FILE.is_file() else 'not found'})"
    )
    print(f"Priority: environment > .env > default\n")  # noqa: T201
    for _setting, _value, _source in Config.describe():
        print(f"  {_setting:<18} {str(_value):<42} [{_source}]")  # noqa: T201
    if _WARNINGS:
        print(  # noqa: T201
            "\nProblems found (the defaults above were used for these):"
        )  # noqa: T201
        for _message in _WARNINGS:
            print(f"  - {_message}")  # noqa: T201
    else:
        print("\nNo problems found.")  # noqa: T201
