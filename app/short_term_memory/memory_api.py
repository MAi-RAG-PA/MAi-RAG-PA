import aiosqlite
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from pathlib import Path

router = APIRouter()

DB_PATH = str(Path.home() / "MAi-RAG" / "memory" / "memory_store.db")

# Initialize DB schema on startup
@router.on_event("startup")
async def startup():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                tags TEXT DEFAULT '',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, key)
            )
        """)
        await db.commit()

# Pydantic models

class MemoryEntry(BaseModel):
    user_id: str = Field(..., description="User identifier")
    key: str = Field(..., description="Memory key (unique per user)")
    value: str = Field(..., description="Memory content")
    category: Optional[str] = Field("general", description="Category of memory (e.g., calendar, client, person)")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for filtering/search")

class MemoryUpdate(BaseModel):
    value: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class MemoryItem(BaseModel):
    id: int
    user_id: str
    key: str
    value: str
    category: str
    tags: List[str]
    timestamp: datetime

class MemoryQuery(BaseModel):
    user_id: str
    key: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 10
    offset: int = 0

# Helper to serialize tags list to string and back
def serialize_tags(tags: List[str]) -> str:
    return ",".join(tags) if tags else ""

def deserialize_tags(tags_str: str) -> List[str]:
    return tags_str.split(",") if tags_str else []

# API Endpoints

@router.post("/memory/store", response_model=MemoryItem)
async def store_memory(entry: MemoryEntry):
    tags_str = serialize_tags(entry.tags)
    async with aiosqlite.connect(DB_PATH) as db:
        # Upsert: insert or update if key exists for user
        await db.execute("""
            INSERT INTO memory (user_id, key, value, category, tags, timestamp)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, key) DO UPDATE SET
                value=excluded.value,
                category=excluded.category,
                tags=excluded.tags,
                timestamp=CURRENT_TIMESTAMP
        """, (entry.user_id, entry.key, entry.value, entry.category, tags_str))
        await db.commit()

        cursor = await db.execute("SELECT id, user_id, key, value, category, tags, timestamp FROM memory WHERE user_id = ? AND key = ?", (entry.user_id, entry.key))
        row = await cursor.fetchone()

    if row:
        return MemoryItem(
            id=row[0],
            user_id=row[1],
            key=row[2],
            value=row[3],
            category=row[4],
            tags=deserialize_tags(row[5]),
            timestamp=row[6]
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to store memory")

@router.get("/memory/retrieve", response_model=List[MemoryItem])
async def retrieve_memory(
    user_id: str,
    key: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    query = "SELECT id, user_id, key, value, category, tags, timestamp FROM memory WHERE user_id = ?"
    params = [user_id]

    if key:
        query += " AND key = ?"
        params.append(key)
    if category:
        query += " AND category = ?"
        params.append(category)
    if tags:
        # Simple tags filtering: memory must contain all tags (comma separated)
        for tag in tags:
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

    results = [
        MemoryItem(
            id=row[0],
            user_id=row[1],
            key=row[2],
            value=row[3],
            category=row[4],
            tags=deserialize_tags(row[5]),
            timestamp=row[6]
        )
        for row in rows
    ]
    return results

@router.patch("/memory/update/{user_id}/{key}", response_model=MemoryItem)
async def update_memory(user_id: str, key: str, update: MemoryUpdate):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, value, category, tags FROM memory WHERE user_id = ? AND key = ?", (user_id, key))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Memory entry not found")

        new_value = update.value if update.value is not None else row[1]
        new_category = update.category if update.category is not None else row[2]
        new_tags = serialize_tags(update.tags) if update.tags is not None else row[3]

        await db.execute("""
            UPDATE memory SET value = ?, category = ?, tags = ?, timestamp = CURRENT_TIMESTAMP
            WHERE user_id = ? AND key = ?
        """, (new_value, new_category, new_tags, user_id, key))
        await db.commit()

        cursor = await db.execute("SELECT id, user_id, key, value, category, tags, timestamp FROM memory WHERE user_id = ? AND key = ?", (user_id, key))
        updated_row = await cursor.fetchone()

    return MemoryItem(
        id=updated_row[0],
        user_id=updated_row[1],
        key=updated_row[2],
        value=updated_row[3],
        category=updated_row[4],
        tags=deserialize_tags(updated_row[5]),
        timestamp=updated_row[6]
    )

@router.delete("/memory/delete/{user_id}/{key}")
async def delete_memory(user_id: str, key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM memory WHERE user_id = ? AND key = ?", (user_id, key))
        await db.commit()
    return {"status": "memory deleted"}

# Utility function to build prompt with recent memories
@router.get("/memory/build_prompt")
async def build_prompt(user_id: str, limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM memory WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        memories = await cursor.fetchall()

    memories_text = "\n".join([m[0] for m in memories]) if memories else ""
    prompt = f"Memories:\n{memories_text}\n\nUser query: {{query}}\nAnswer:"
    return {"prompt_template": prompt}
