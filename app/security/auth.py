# app/security/auth.py
"""
Simple token-based authentication for MAi-RAG.
Uses a configurable API key stored in SQLite settings.
No external auth providers needed - fully self-contained.
"""
import logging
import secrets
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> str:
    """Generate a new secure API key."""
    return secrets.token_urlsafe(32)


async def get_current_api_key(request: Request) -> Optional[str]:
    """Extract API key from request header or query param."""
    key = request.headers.get("X-API-Key")
    if key:
        return key
    return request.query_params.get("api_key")


async def verify_api_key(request: Request) -> str:
    """Verify the API key against stored value. Raises 401/403 on failure."""
    from app.main import get_sqlite_manager

    provided_key = await get_current_api_key(request)
    if not provided_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Set X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    mgr = get_sqlite_manager()
    stored_key = mgr.get("api_key")

    if not stored_key:
        raise HTTPException(
            status_code=401,
            detail="No API key configured. Generate one via POST /api/auth/generate-key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not secrets.compare_digest(provided_key, stored_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return provided_key


async def optional_auth(request: Request) -> bool:
    """Check auth but don't fail if no key is set yet."""
    from app.main import get_sqlite_manager

    mgr = get_sqlite_manager()
    if not mgr.get("api_key"):
        return True

    try:
        await verify_api_key(request)
        return True
    except HTTPException:
        raise
