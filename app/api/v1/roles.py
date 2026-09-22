# app/api/v1/roles.py

# GET  /api/roles                  → list all roles
# POST /api/roles                  → create a role
# GET  /api/roles/{id}             → get one role
# PUT  /api/roles/{id}             → update a role
# DELETE /api/roles/{id}           → delete a role
# POST /api/roles/{id}/activate    → set as active role
# GET  /api/roles/active           → get current active role

"""
Roles CRUD API — Phase 1 of the Roles system.

A Role is a self-contained agent configuration:
  - system_prompt       (overrides the global prompt)
  - collection_name     (narrows LTM search to one Qdrant collection)
  - citations_enabled   (per-role citation behaviour)
  - model_override      (optional, overrides the global model selector)

Only ONE role is active at a time; the active role id is stored in
short_term_memory under the key 'active_role_id'.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
DB_PATH = PROJECT_ROOT / "memory" / "memory_store.db"

router = APIRouter(prefix="/roles", tags=["roles"])


# =============================================================================
# Pydantic models
# =============================================================================


class RoleIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    system_prompt: str = Field(..., min_length=1)
    collection_name: Optional[str] = None
    citations_enabled: bool = True
    model_override: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class RoleOut(BaseModel):
    id: str
    name: str
    system_prompt: str
    collection_name: Optional[str]
    citations_enabled: bool
    model_override: Optional[str]
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# =============================================================================
# Helpers
# =============================================================================


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or f"role-{uuid.uuid4().hex[:8]}"


def _row_to_out(row: sqlite3.Row) -> RoleOut:
    return RoleOut(
        id=row["id"],
        name=row["name"],
        system_prompt=row["system_prompt"],
        collection_name=row["collection_name"],
        citations_enabled=bool(row["citations_enabled"]),
        model_override=row["model_override"],
        is_active=bool(row["is_active"]),
        created_at=str(row["created_at"]) if row["created_at"] else None,
        updated_at=str(row["updated_at"]) if row["updated_at"] else None,
    )


def _ensure_unique_id(conn: sqlite3.Connection, base_id: str) -> str:
    candidate = base_id
    suffix = 1
    while conn.execute("SELECT 1 FROM roles WHERE id = ?", (candidate,)).fetchone():
        suffix += 1
        candidate = f"{base_id}-{suffix}"
    return candidate


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=List[RoleOut])
def list_roles():
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM roles ORDER BY is_active DESC, name ASC"
        ).fetchall()
    return [_row_to_out(r) for r in rows]


@router.get("/active", response_model=Optional[RoleOut])
def get_active_role():
    with _conn() as conn:
        row = conn.execute("SELECT * FROM roles WHERE is_active = 1 LIMIT 1").fetchone()
    return _row_to_out(row) if row else None


@router.get("/{role_id}", response_model=RoleOut)
def get_role(role_id: str):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found")
    return _row_to_out(row)


@router.post("", response_model=RoleOut, status_code=201)
def create_role(payload: RoleIn):
    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM roles WHERE LOWER(name) = LOWER(?)", (payload.name,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"A role named '{payload.name}' already exists",
            )
        new_id = _ensure_unique_id(conn, _slugify(payload.name))
        conn.execute(
            """
            INSERT INTO roles
                (id, name, system_prompt, collection_name, citations_enabled,
                 model_override, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                new_id,
                payload.name,
                payload.system_prompt,
                payload.collection_name,
                1 if payload.citations_enabled else 0,
                payload.model_override,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (new_id,)).fetchone()
    logger.info("Created role '%s' (id=%s)", payload.name, new_id)
    return _row_to_out(row)


@router.put("/{role_id}", response_model=RoleOut)
def update_role(role_id: str, payload: RoleIn):
    with _conn() as conn:
        if not conn.execute("SELECT 1 FROM roles WHERE id = ?", (role_id,)).fetchone():
            raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found")
        clash = conn.execute(
            "SELECT id FROM roles WHERE LOWER(name) = LOWER(?) AND id != ?",
            (payload.name, role_id),
        ).fetchone()
        if clash:
            raise HTTPException(
                status_code=409,
                detail=f"A role named '{payload.name}' already exists",
            )
        conn.execute(
            """
            UPDATE roles SET
                name = ?, system_prompt = ?, collection_name = ?,
                citations_enabled = ?, model_override = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                payload.name,
                payload.system_prompt,
                payload.collection_name,
                1 if payload.citations_enabled else 0,
                payload.model_override,
                role_id,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
    logger.info("Updated role '%s' (id=%s)", payload.name, role_id)
    return _row_to_out(row)


@router.delete("/{role_id}")
def delete_role(role_id: str):
    if role_id == "default":
        raise HTTPException(
            status_code=400, detail="The Default role cannot be deleted"
        )
    with _conn() as conn:
        if not conn.execute("SELECT 1 FROM roles WHERE id = ?", (role_id,)).fetchone():
            raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found")
        conn.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        conn.commit()
    logger.info("Deleted role id=%s", role_id)
    return {"status": "deleted", "id": role_id}


@router.post("/{role_id}/activate", response_model=RoleOut)
def activate_role(role_id: str):
    with _conn() as conn:
        if not conn.execute("SELECT 1 FROM roles WHERE id = ?", (role_id,)).fetchone():
            raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found")
        conn.execute("UPDATE roles SET is_active = 0")
        conn.execute(
            "UPDATE roles SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (role_id,),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
    logger.info("Activated role '%s' (id=%s)", row["name"], role_id)
    return _row_to_out(row)
