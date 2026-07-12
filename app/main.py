# app/main.py
"""
MAi-RAG-PA API - Main Application
Production-ready FastAPI backend with comprehensive endpoint coverage.
"""

# CRITICAL: Set offline mode for HuggingFace BEFORE any other imports
import os

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/models"
)

import asyncio
import hashlib
import json
import logging
import re
import shutil
import subprocess
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
# Now import everything else
from typing import Any, List, Optional

import ollama
import psutil
from fastapi import (Depends, FastAPI, File, Form, HTTPException, Query,
                     Request, UploadFile, WebSocket, WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, field_validator
from qdrant_client import models
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

# Agent logic
from app.agents.agent_core import (_get_llm, agentic_create_file,
                                   clear_model_cache, get_default_model,
                                   get_rag_status, get_system_prompt,
                                   process_request)
from app.api.v1.router import router as v1_router
from app.documents.chunker import chunk_text_semantic as chunk_text
from app.documents.parser import parse_file as parser_parse_file
from app.documents.processor import process_directory
# Memory managers
from app.memory.qdrant_manager import QdrantMemoryManager
from app.memory.sqlite_memory import SQLiteMemoryManager
from app.metrics import (ACTIVE_CONNECTIONS, CONTENT_TYPE_LATEST,
                         DATABASE_SIZE_BYTES, MODEL_DURATION,
                         MODEL_REQUEST_COUNT, MetricsMiddleware,
                         generate_latest)
from app.rag.model_manager import ModelManager
# Import the router here, but don't attach it yet
from app.rag.rag_server import router as rag_router
from app.security.auth import (api_key_header, generate_api_key, optional_auth,
                               verify_api_key)
from app.security.input_validation import sanitize_filename
from app.security.rate_limiter import limiter, rate_limit_exceeded_handler
from app.websocket_manager import ws_manager

# =============================================================================
# Configuration
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
WORKSPACE_PATH = PROJECT_ROOT / "workspace"
WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)
DB_PATH = PROJECT_ROOT / "memory" / "memory_store.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Failsafe Responses
# =============================================================================
INADEQUATE_MODEL_RESPONSE = """I apologize, but I'm having difficulty generating a quality response with my current model configuration. This can happen with complex requests that require more reasoning capability.

**Suggestions:**
1. Try selecting a larger model from the dropdown (14b, 32b, or higher)
2. Break your request into smaller, simpler parts
3. Rephrase your question more directly

If you continue experiencing issues, please try a more capable model for this type of task."""

# =============================================================================
# Logging Setup (Structured Logging via structlog)
# =============================================================================
from app.utils.structured_logging import setup_logging

logger = setup_logging(log_level="INFO")

# ---------------------------------------------------------------------------
# Chunk-and-Ingest Helpers (private — place above chunk_and_ingest endpoint)
# ---------------------------------------------------------------------------


def route_to_specialist(user_query: str) -> dict:
    """Simple keyword-based routing - no LLM overhead."""
    query_lower = user_query.lower()

    # SQL query detection
    sql_keywords = [
        "select",
        "show",
        "list",
        "find",
        "count",
        "what are my",
        "show my",
        "how many",
    ]
    if any(kw in query_lower for kw in sql_keywords):
        return {"specialist": "sql", "confidence": 0.9}

    # Default to chat
    return {"specialist": "chat", "confidence": 0.5}


def _content_hash(text: str) -> str:
    """Generate a deterministic hash of chunk content for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


async def _phase1_chunk_text_to_disk(
    text: str,
    source: str,
    cache_dir: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[int, list[str]]:
    """Phase 1: Chunk text → write each chunk as .txt + .json to a per-source subdirectory.

    Directory structure: cache_dir/{safe_source}/{safe_source}_chunk_{index}.txt|.json
    Only ONE chunk is ever in memory at a time.
    Duplicate chunks (by content hash) are skipped entirely.

    Returns (unique_chunk_count, list_of_content_hashes).
    """
    safe_source = sanitize_filename(source.replace("/", "_").replace("\\", "_"))
    file_cache_dir = cache_dir / safe_source
    file_cache_dir.mkdir(parents=True, exist_ok=True)

    chunks = chunk_text(text, max_words=chunk_size, overlap_sentences=2)
    if not chunks:
        return 0, []

    seen_hashes: set[str] = set()
    written_hashes: list[str] = []
    chunk_index = 0

    for chunk in chunks:
        h = _content_hash(chunk)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        base_name = f"{safe_source}_chunk_{chunk_index:05d}"

        txt_path = file_cache_dir / f"{base_name}.txt"
        txt_path.write_text(chunk, encoding="utf-8")

        meta = {
            "source": source,
            "chunk_index": chunk_index,
            "total_chunks": None,
            "content_hash": h,
            "char_count": len(chunk),
        }
        json_path = file_cache_dir / f"{base_name}.json"
        json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        written_hashes.append(h)
        chunk_index += 1

    total = len(written_hashes)
    for i in range(total):
        base_name = f"{safe_source}_chunk_{i:05d}"
        json_path = file_cache_dir / f"{base_name}.json"
        if json_path.exists():
            meta = json.loads(json_path.read_text(encoding="utf-8"))
            meta["total_chunks"] = total
            json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    logger.info(f"Phase 1 complete: {total} unique chunks written to {file_cache_dir}")
    return total, written_hashes


async def _phase1_chunk_file_to_disk(
    file_path: Path,
    source_label: str,
    cache_dir: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[int, list[str], bool]:
    """Phase 1: Parse file → write chunks/records to disk.

    Returns (count, hashes, is_structured).
    If is_structured is True, we wrote JSON records instead of text chunks.
    """
    safe_source = sanitize_filename(source_label.replace("/", "_").replace("\\", "_"))
    file_cache_dir = cache_dir / safe_source
    file_cache_dir.mkdir(parents=True, exist_ok=True)

    text_chunks, structured_records = parser_parse_file(file_path)

    written_count = 0
    written_hashes = []
    seen_hashes = set()

    if structured_records:
        for idx, record in enumerate(structured_records):
            text_for_embedding = " ".join(
                [str(v) for v in record.values() if isinstance(v, (str, int, float))]
            )

            h = _content_hash(text_for_embedding)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            base_name = f"{safe_source}_record_{idx:05d}"

            meta = {
                "source": source_label,
                "index": idx,
                "total": len(structured_records),
                "content_hash": h,
                "payload": record,
                "embedding_text": text_for_embedding,
            }

            json_path = file_cache_dir / f"{base_name}.json"
            json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

            written_hashes.append(h)
            written_count += 1

        logger.info(
            f"Phase 1 complete: {written_count} structured records written for '{source_label}'"
        )
        return written_count, written_hashes, True

    if not text_chunks:
        return 0, [], False

    chunk_index = 0
    for chunk in text_chunks:
        sub_chunks = chunk_text(chunk, max_words=chunk_size, overlap_sentences=2)

        for sub_chunk in sub_chunks:
            h = _content_hash(sub_chunk)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            base_name = f"{safe_source}_chunk_{chunk_index:05d}"

            txt_path = file_cache_dir / f"{base_name}.txt"
            txt_path.write_text(sub_chunk, encoding="utf-8")

            meta = {
                "source": source_label,
                "chunk_index": chunk_index,
                "total_chunks": None,
                "content_hash": h,
                "char_count": len(sub_chunk),
                "type": "text",
            }
            json_path = file_cache_dir / f"{base_name}.json"
            json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

            written_hashes.append(h)
            chunk_index += 1

    total = len(written_hashes)
    for i in range(total):
        base_name = f"{safe_source}_chunk_{i:05d}"
        json_path = file_cache_dir / f"{base_name}.json"
        if json_path.exists():
            meta = json.loads(json_path.read_text(encoding="utf-8"))
            meta["total_chunks"] = total
            json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    logger.info(f"Phase 1 complete: {total} text chunks written for '{source_label}'")
    return total, written_hashes, False


def _get_existing_hashes_batch(qm, collection: str, hashes: list[str]) -> set[str]:
    """Batch query Qdrant for existing content hashes."""
    import sys

    if not hashes:
        return set()
    try:
        conditions = [
            models.FieldCondition(key="content_hash", match=models.MatchValue(value=h))
            for h in hashes
        ]
        results = qm.client.scroll(
            collection_name=collection,
            scroll_filter=models.Filter(should=conditions),
            limit=len(hashes),
            with_payload=["content_hash"],
            with_vectors=False,
        )
        found = {p.payload.get("content_hash") for p in results[0] if p.payload}
        print(
            f"    DEDUP: checked {len(hashes)} hashes, found {len(found)} existing",
            file=sys.stderr,
            flush=True,
        )
        return found
    except Exception as e:
        print(f"    DEDUP FAILED: {e}", file=sys.stderr, flush=True)
        import traceback

        traceback.print_exc(file=sys.stderr)
        return set()


async def _phase2_ingest_from_disk(
    cache_dir: Path,
    source: str,
    qm,
    collection: str,
    ws_manager,
    total_chunks_ref: list,
    skipped_duplicates_ref: list,
    files_processed_ref: list,
    is_structured: bool,
) -> int:
    """Phase 2: Ingest from disk. Handles both text chunks and structured records."""
    BATCH_SIZE = 64
    safe_source = sanitize_filename(source.replace("/", "_").replace("\\", "_"))
    file_cache_dir = cache_dir / safe_source

    if not file_cache_dir.exists():
        return 0

    ingested = 0

    if is_structured:
        json_files = sorted(file_cache_dir.glob(f"{safe_source}_record_*.json"))
        total_file_chunks = len(json_files)

        try:
            for batch_start in range(0, total_file_chunks, BATCH_SIZE):
                batch_json = json_files[batch_start : batch_start + BATCH_SIZE]

                batch_hashes = []
                batch_data = []
                for jf in batch_json:
                    meta = json.loads(jf.read_text(encoding="utf-8"))
                    batch_hashes.append(meta["content_hash"])
                    batch_data.append(meta)

                existing = _get_existing_hashes_batch(qm, collection, batch_hashes)

                documents = []
                for meta in batch_data:
                    if meta["content_hash"] in existing:
                        continue
                    documents.append(
                        {
                            "content": meta["embedding_text"],
                            "source": meta["source"],
                            "chunk_index": meta["index"],
                            "total_chunks": meta["total"],
                            "content_hash": meta["content_hash"],
                            "payload": meta["payload"],
                        }
                    )

                skipped = len(batch_hashes) - len(documents)
                if skipped > 0:
                    skipped_duplicates_ref[0] += skipped

                if not documents:
                    continue

                result = qm.ingest_documents(collection, documents)
                if result.get("status") == "success":
                    ingested += result.get("ingested", len(documents))

                try:
                    await ws_manager.broadcast(
                        {
                            "type": "ingest_progress",
                            "source": source,
                            "chunks_ingested": total_chunks_ref[0] + ingested,
                            "current_file_chunks": ingested,
                            "total_file_chunks": total_file_chunks,
                            "files_processed": files_processed_ref[0],
                        }
                    )
                except Exception:
                    pass

            total_chunks_ref[0] += ingested

        except Exception as e:
            logger.error(f"Phase 2 failed for structured data '{source}': {e}")
            raise
        else:
            if file_cache_dir.exists():
                shutil.rmtree(file_cache_dir)

    else:
        json_files = sorted(file_cache_dir.glob(f"{safe_source}_chunk_*.json"))
        total_file_chunks = len(json_files)

        try:
            for batch_start in range(0, total_file_chunks, BATCH_SIZE):
                batch_json = json_files[batch_start : batch_start + BATCH_SIZE]

                batch_hashes = []
                batch_data = []
                for jf in batch_json:
                    meta = json.loads(jf.read_text(encoding="utf-8"))
                    txt_path = jf.with_suffix(".txt")
                    content = txt_path.read_text(encoding="utf-8")
                    batch_hashes.append(meta["content_hash"])
                    batch_data.append((content, meta))

                existing = _get_existing_hashes_batch(qm, collection, batch_hashes)

                documents = []
                for content, meta in batch_data:
                    if meta["content_hash"] in existing:
                        continue
                    documents.append(
                        {
                            "content": content,
                            "source": meta["source"],
                            "chunk_index": meta["chunk_index"],
                            "total_chunks": meta["total_chunks"],
                            "content_hash": meta["content_hash"],
                        }
                    )

                skipped = len(batch_hashes) - len(documents)
                if skipped > 0:
                    skipped_duplicates_ref[0] += skipped

                if not documents:
                    continue

                result = qm.ingest_documents(collection, documents)
                if result.get("status") == "success":
                    ingested += result.get("ingested", len(documents))

                try:
                    await ws_manager.broadcast(
                        {
                            "type": "ingest_progress",
                            "source": source,
                            "chunks_ingested": total_chunks_ref[0] + ingested,
                            "current_file_chunks": ingested,
                            "total_file_chunks": total_file_chunks,
                            "files_processed": files_processed_ref[0],
                        }
                    )
                except Exception:
                    pass

            total_chunks_ref[0] += ingested

        except Exception as e:
            logger.error(f"Phase 2 failed for text '{source}': {e}")
            raise
        else:
            if file_cache_dir.exists():
                shutil.rmtree(file_cache_dir)

    return ingested


# =============================================================================
# Environment Checker
# =============================================================================


class EnvironmentChecker:
    """Check if required services are available."""

    def __init__(self):
        self.ollama_available = False
        self.qdrant_available = False
        self.ollama_url = "http://127.0.0.1:11434"
        self.qdrant_url = "http://127.0.0.1:6333"

    def check_ollama(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                models = data.get("models", [])
                self.ollama_available = True
                logger.info(f"Ollama is running with {len(models)} models")
                return True
        except Exception as e:
            self.ollama_available = False
            logger.warning(f"Ollama not available: {e}")
            return False

    def check_qdrant(self) -> bool:
        """Check if Qdrant is running and accessible."""
        try:
            req = urllib.request.Request(f"{self.qdrant_url}/collections", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                collections = data.get("result", {}).get("collections", [])
                self.qdrant_available = True
                logger.info(f"Qdrant is running with {len(collections)} collections")
                return True
        except Exception as e:
            self.qdrant_available = False
            logger.warning(f"Qdrant not available: {e}")
            return False

    def check_all(self) -> dict:
        """Run all environment checks."""
        self.check_ollama()
        self.check_qdrant()

        return {
            "ollama": {
                "available": self.ollama_available,
                "url": self.ollama_url,
                "download_url": "https://ollama.com/download",
            },
            "qdrant": {
                "available": self.qdrant_available,
                "url": self.qdrant_url,
                "download_url": "https://github.com/qdrant/qdrant/releases/",
            },
            "all_services_available": self.ollama_available and self.qdrant_available,
        }


env_checker = EnvironmentChecker()

# =============================================================================
# FastAPI App Setup
# =============================================================================
executor = ThreadPoolExecutor(max_workers=4)

app = FastAPI(
    title="MAi-RAG-PA API",
    version="2.0.0",
    description="Personal AI Assistant with RAG, Tool-Calling, and Agentic Workflows",
)

_cors_origins = (
    os.environ.get("CORS_ORIGINS", "").split(",")
    if os.environ.get("CORS_ORIGINS")
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

app.include_router(rag_router, prefix="/api/rag", tags=["RAG"])
app.include_router(v1_router, prefix="/api/v1", tags=["API v1"])
app.add_middleware(MetricsMiddleware)

sqlite_manager: Optional[SQLiteMemoryManager] = None
qdrant_manager: Optional[QdrantMemoryManager] = None

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

heartbeat_task: Optional[asyncio.Task] = None
shutdown_flag = False


def get_sqlite_manager() -> SQLiteMemoryManager:
    """Lazy initialization of SQLite manager."""
    global sqlite_manager
    if sqlite_manager is None:
        sqlite_manager = SQLiteMemoryManager(db_path=DB_PATH)
        logger.info(f"SQLite manager initialized at: {sqlite_manager.db_path}")
    return sqlite_manager


def get_qdrant_manager() -> QdrantMemoryManager:
    """Lazy initialization of Qdrant manager."""
    global qdrant_manager
    if qdrant_manager is None:
        qdrant_manager = QdrantMemoryManager()
    return qdrant_manager


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request too large",
                    "detail": "Maximum request size is 10MB",
                },
            )
        return await call_next(request)


app.add_middleware(RequestSizeLimitMiddleware)

model_manager = ModelManager()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler to expose errors that bypass endpoint-level try/except."""
    import sys
    import traceback

    print(
        f"!!! GLOBAL EXCEPTION on {request.method} {request.url.path}: {exc}",
        file=sys.stderr,
        flush=True,
    )
    traceback.print_exc(file=sys.stderr)
    return JSONResponse(
        status_code=500, content={"detail": f"Internal error: {str(exc)}"}
    )


# =============================================================================
# Pydantic Models
# =============================================================================


class AgentRequest(BaseModel):
    query: str
    filename: Optional[str] = None
    model: Optional[str] = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        from app.security.input_validation import (MAX_QUERY_LENGTH,
                                                   sanitize_string)

        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return sanitize_string(v.strip(), MAX_QUERY_LENGTH)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v):
        if v is None:
            return v
        from app.security.input_validation import sanitize_filename

        return sanitize_filename(v)

    @field_validator("model")
    @classmethod
    def validate_model(cls, v):
        if v is None:
            return v
        if not re.match(r"^[a-zA-Z0-9._:-]+$", v):
            raise ValueError("Invalid model name format")
        return v[:100]


class FileCreationRequest(BaseModel):
    filename: str
    description: str
    model: Optional[str] = None


class DirectoryCreationRequest(BaseModel):
    path: str


class NoteSaveRequest(BaseModel):
    filename: str
    content: str

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v):
        from app.security.input_validation import sanitize_filename

        return sanitize_filename(v)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        from app.security.input_validation import (MAX_CONTENT_LENGTH,
                                                   sanitize_string)

        return sanitize_string(v, MAX_CONTENT_LENGTH)


class CollectionRequest(BaseModel):
    name: str
    action: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        from app.security.input_validation import validate_collection_name

        return validate_collection_name(v)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v):
        allowed = ["create", "delete"]
        if v not in allowed:
            raise ValueError(f"Action must be one of {allowed}")
        return v


class IngestRequest(BaseModel):
    collection: str
    documents: List[dict]


class SearchRequest(BaseModel):
    collection: str
    query: str
    top_k: int = 5


class EventRequest(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    category: str = "general"
    is_recurring: bool = False
    recurrence_type: Optional[str] = None
    recurrence_days: Optional[List[str]] = None
    recurrence_end_date: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        from app.security.input_validation import (MAX_TITLE_LENGTH,
                                                   sanitize_string)

        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return sanitize_string(v.strip(), MAX_TITLE_LENGTH)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is None:
            return v
        from app.security.input_validation import sanitize_string

        return sanitize_string(v)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        allowed = ["general", "appointment", "reminder", "work", "personal"]
        if v not in allowed:
            return "general"
        return v


class ReminderRequest(BaseModel):
    id: Optional[str] = None
    text: str
    due_time: str
    priority: str = "medium"
    completed: bool = False

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        from app.security.input_validation import (MAX_TITLE_LENGTH,
                                                   sanitize_string)

        if not v or not v.strip():
            raise ValueError("Reminder text cannot be empty")
        return sanitize_string(v.strip(), MAX_TITLE_LENGTH)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        allowed = ["low", "medium", "high"]
        return v if v in allowed else "medium"


class TodoRequest(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    completed: bool = False
    due_date: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        from app.security.input_validation import (MAX_TITLE_LENGTH,
                                                   sanitize_string)

        if not v or not v.strip():
            raise ValueError("Todo title cannot be empty")
        return sanitize_string(v.strip(), MAX_TITLE_LENGTH)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is None:
            return v
        from app.security.input_validation import sanitize_string

        return sanitize_string(v)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        allowed = ["low", "medium", "high"]
        return v if v in allowed else "medium"


class UserProfileRequest(BaseModel):
    key: str
    value: Any


class ChatMessageRequest(BaseModel):
    thread_id: str
    role: str
    content: str
    message_id: Optional[str] = None
    timestamp: Optional[int] = None
    model: Optional[str] = None
    filename: Optional[str] = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        from app.security.input_validation import (MAX_CONTENT_LENGTH,
                                                   sanitize_string)

        if not v:
            raise ValueError("Message content cannot be empty")
        return sanitize_string(v, MAX_CONTENT_LENGTH)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed = ["user", "assistant", "system"]
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v


class ChatThreadRequest(BaseModel):
    id: str
    title: str


class SettingsRequest(BaseModel):
    key: str
    value: Any


class DirectoryIngestRequest(BaseModel):
    directory: str
    collection: str
    chunk_size: int = 1000
    chunk_overlap: int = 200
    file_extensions: Optional[List[str]] = None


class SyntheticDataRequest(BaseModel):
    collection: str
    topic: str
    num_samples: int = 10
    purpose: str = "constraint_validation"
    compliance_threshold: int = 95


class DeleteDocumentRequest(BaseModel):
    collection: str
    document_ids: List[str]


# =============================================================================
# Security Helpers
# =============================================================================


def resolve_project_path(user_path: str) -> Path:
    """Securely resolve a path within the project root."""
    expanded = Path(user_path).expanduser().resolve()
    project_abs = PROJECT_ROOT.resolve()

    forbidden = ["venv", "node_modules", ".git", "__pycache__", ".env"]
    for forbidden_dir in forbidden:
        if forbidden_dir in expanded.parts:
            raise ValueError(f"Access to '{forbidden_dir}' is strictly forbidden.")

    try:
        expanded.relative_to(project_abs)
        return expanded
    except ValueError:
        raise ValueError(
            f"Path traversal detected: '{user_path}' resolves outside project root"
        )


def resolve_workspace_path(user_path: str) -> Path:
    """Securely resolve a path, anchoring relative paths to the workspace."""
    path = Path(user_path)

    if not path.is_absolute():
        path = WORKSPACE_PATH / path

    expanded = path.expanduser().resolve()
    workspace_abs = WORKSPACE_PATH.resolve()

    try:
        expanded.relative_to(workspace_abs)
        return expanded
    except ValueError:
        raise ValueError(
            f"Path traversal detected: '{user_path}' resolves outside workspace"
        )


# =============================================================================
# Health & System Endpoints
# =============================================================================


@app.get("/api/system/protected-models")
async def get_protected_models_status_endpoint(api_key: str = Depends(verify_api_key)):
    """Get status of protected system models."""
    from app.agents.agent_core import get_protected_models_status

    protected = get_protected_models_status()

    return {
        "protected_models": protected,
        "message": "These models are recommended for optimal system performance. Removing them may affect functionality.",
    }


@app.post("/api/system/dev-sandbox/init")
async def init_dev_sandbox(api_key: str = Depends(verify_api_key)):
    """Initialize the MAi-RAG-DEV sandbox for self-healing operations."""
    from app.agents.agent_core import initialize_dev_sandbox

    result = initialize_dev_sandbox()

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@app.get("/api/system/dev-sandbox/status")
async def get_dev_sandbox_status(api_key: str = Depends(verify_api_key)):
    """Get the status of the MAi-RAG-DEV sandbox."""
    from app.agents.agent_core import SANDBOX_ROOT

    if not SANDBOX_ROOT.exists():
        return {
            "status": "not_initialized",
            "path": str(SANDBOX_ROOT),
            "message": "Sandbox not initialized. Use POST /api/system/dev-sandbox/init",
        }

    # Count files
    file_count = sum(1 for _ in SANDBOX_ROOT.rglob("*") if _.is_file())
    dir_count = sum(1 for _ in SANDBOX_ROOT.rglob("*") if _.is_dir())

    return {
        "status": "initialized",
        "path": str(SANDBOX_ROOT),
        "file_count": file_count,
        "directory_count": dir_count,
        "message": "Sandbox is ready for self-healing operations",
    }


@app.delete("/api/system/dev-sandbox/reset")
async def reset_dev_sandbox(api_key: str = Depends(verify_api_key)):
    """Reset the MAi-RAG-DEV sandbox (delete and recreate)."""
    import shutil

    from app.agents.agent_core import SANDBOX_ROOT, initialize_dev_sandbox

    if SANDBOX_ROOT.exists():
        try:
            shutil.rmtree(SANDBOX_ROOT)
            logger.info("Deleted existing sandbox")
        except Exception as e:
            logger.error(f"Failed to delete sandbox: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to delete sandbox: {str(e)}"
            )

    result = initialize_dev_sandbox()

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return {**result, "message": "Sandbox reset successfully"}


@app.get("/api/system/hardware")
async def get_hardware_info(api_key: str = Depends(verify_api_key)):
    """Get system hardware information and recommendations."""
    import psutil

    from app.agents.agent_core import detect_hardware_capabilities

    hw_caps = detect_hardware_capabilities()

    return {
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "cpu_cores": psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True),
        "recommendations": hw_caps,
        "message": f"System tier: {hw_caps['tier'].upper()}",
    }


@app.get("/api/system/cpu")
async def get_system_cpu():
    """Get CPU usage percentage."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        return {"percent": cpu_percent}
    except Exception as e:
        logger.error(f"Failed to get CPU usage: {e}", exc_info=True)
        return {"percent": 0, "error": str(e)}


@app.get("/api/system/ram")
async def get_system_ram():
    """Get system RAM and swap usage."""
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "used": mem.used // (1024 * 1024),
            "total": mem.total // (1024 * 1024),
            "percent": mem.percent,
            "swap_used": swap.used // (1024 * 1024),
            "swap_total": swap.total // (1024 * 1024),
            "swap_percent": swap.percent,
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}", exc_info=True)
        return {
            "used": 0,
            "total": 0,
            "percent": 0,
            "swap_used": 0,
            "swap_total": 0,
            "swap_percent": 0,
            "error": str(e),
        }


@app.get("/api/version")
async def get_api_version():
    """List available API versions."""
    return {
        "current": "v1",
        "available": ["v1"],
        "deprecated": [],
        "base_url": "/api/v1",
    }


@app.get("/api/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    from app.metrics import (ACTIVE_CONNECTIONS, CONTENT_TYPE_LATEST,
                             DATABASE_SIZE_BYTES, generate_latest)

    try:
        if DB_PATH.exists():
            DATABASE_SIZE_BYTES.set(DB_PATH.stat().st_size)
    except Exception:
        pass

    try:
        ACTIVE_CONNECTIONS.set(ws_manager.client_count)
    except Exception:
        pass

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/system/workspace-path")
async def get_workspace_path():
    """Return the absolute workspace path for frontend path construction."""
    return {"workspace_path": str(WORKSPACE_PATH)}


@app.get("/api/system/environment")
async def check_environment():
    """Check if required services (Ollama, Qdrant) are available."""
    try:
        status = env_checker.check_all()
        return status
    except Exception as e:
        logger.error(f"Environment check failed: {e}", exc_info=True)
        return {
            "ollama": {"available": False, "error": str(e)},
            "qdrant": {"available": False, "error": str(e)},
            "all_services_available": False,
        }


@app.get("/api/health")
@limiter.limit("120/minute")
async def health_check(request: Request):
    """Comprehensive health check for monitoring tools."""
    import time

    start = time.time()

    checks = {}
    overall_status = "healthy"

    try:
        mgr = get_sqlite_manager()
        with mgr.get_cursor() as cur:
            cur.execute("SELECT 1")
        checks["database"] = {"status": "healthy", "path": str(mgr.db_path)}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    try:
        qm = get_qdrant_manager()
        if qm.qdrant_available:
            checks["vector_store"] = {"status": "healthy"}
        else:
            checks["vector_store"] = {"status": "degraded", "detail": "not connected"}
            if overall_status == "healthy":
                overall_status = "degraded"
    except Exception as e:
        checks["vector_store"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            model_count = len(data.get("models", []))
            checks["llm"] = {"status": "healthy", "models": model_count}
    except Exception as e:
        checks["llm"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    checks["workspace"] = {
        "status": "healthy" if os.access(WORKSPACE_PATH, os.W_OK) else "unhealthy",
        "writable": os.access(WORKSPACE_PATH, os.W_OK),
    }

    response_time_ms = round((time.time() - start) * 1000, 2)
    status_code = (
        200
        if overall_status == "healthy"
        else (503 if overall_status == "unhealthy" else 200)
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "response_time_ms": response_time_ms,
            "checks": checks,
            "version": "2.0.0",
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.get("/api/health/live")
async def liveness_probe():
    """Fast liveness probe - no external dependencies."""
    return {"status": "alive"}


@app.get("/api/health/ready")
async def readiness_probe(request: Request):
    """Readiness probe - checks if app can serve requests."""
    try:
        mgr = get_sqlite_manager()
        with mgr.get_cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(
            status_code=503, content={"status": "not_ready", "error": str(e)}
        )


@app.get("/api/system/status")
async def get_system_status():
    """Check if MAi-RAG-PA services are running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn app.main:app"], capture_output=True, text=True
        )
        is_running = result.returncode == 0

        return {
            "status": "running" if is_running else "stopped",
            "pid": result.stdout.strip().split("\n")[0] if is_running else None,
        }
    except Exception as e:
        logger.error(f"Failed to check system status: {e}")
        return {"status": "unknown", "error": str(e)}


@app.post("/api/system/stop")
async def stop_system():
    """Stop MAi-RAG-PA services gracefully."""
    try:
        stop_script = PROJECT_ROOT / "stop.sh"
        if stop_script.exists():
            subprocess.Popen(["bash", str(stop_script)], start_new_session=True)
            return {"status": "stopping", "message": "MAi-RAG-PA is shutting down..."}
        else:
            return {"status": "error", "message": "stop.sh not found"}
    except Exception as e:
        logger.error(f"Failed to stop system: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/system/start")
async def start_system():
    """Signal the watchdog to start MAi-RAG-PA"""
    try:
        flag_file = PROJECT_ROOT / "restart.flag"
        flag_file.touch()
        return {"status": "starting", "message": "Restart signal sent to watchdog."}
    except Exception as e:
        logger.error(f"Failed to create restart flag: {e}")
        return {"status": "error", "message": str(e)}


# =============================================================================
# Ollama Model Management
# =============================================================================


@app.get("/api/ollama/models")
async def get_ollama_models():
    """Fetch available models from Ollama."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            models = [model["name"] for model in data.get("models", [])]
            return {"models": models}
    except Exception as e:
        logger.error(f"Failed to fetch Ollama models: {e}")
        return {"models": [], "error": str(e)}


@app.get("/api/models/status")
async def get_model_status(request: Request):
    """Get model availability, fallback chain, and context limits."""
    from app.rag.context_manager import get_context_limit

    available = model_manager.get_available_models(force_refresh=True)
    chat_models = model_manager.get_chat_models()

    chain_status = []
    for model in model_manager._fallback_chain:
        chain_status.append(
            {
                "model": model,
                "available": model in available,
                "context_limit": get_context_limit(model),
            }
        )

    model_details = []
    for m in available:
        model_details.append(
            {
                "name": m,
                "context_limit": get_context_limit(m),
                "is_chat": m in chat_models,
            }
        )

    return {
        "available_models": model_details,
        "chat_models": chat_models,
        "fallback_chain": chain_status,
        "default_model": get_default_model(),
        "default_context_limit": get_context_limit(get_default_model()),
    }


# =============================================================================
# Settings Endpoints
# =============================================================================


@app.post("/api/system/backup")
async def create_full_backup(api_key: str = Depends(verify_api_key)):
    """Create a full backup of SQLite database and all Qdrant collections."""
    results = {
        "sqlite": None,
        "qdrant": {},
        "timestamp": datetime.now().isoformat(),
        "errors": [],
    }

    try:
        try:
            mgr = get_sqlite_manager()
            sqlite_backup = mgr.backup_database()
            results["sqlite"] = str(sqlite_backup) if sqlite_backup else "failed"
        except Exception as e:
            results["sqlite"] = "failed"
            results["errors"].append(f"SQLite backup failed: {str(e)}")
            logger.error(f"SQLite backup failed: {e}", exc_info=True)

        try:
            qm = get_qdrant_manager()
            if qm.qdrant_available:
                collections = qm.list_collections()
                if collections:
                    for collection in collections:
                        try:
                            snapshot_path = qm.create_snapshot(collection)
                            if snapshot_path:
                                qm.rotate_snapshots(collection, keep=7)
                                results["qdrant"][collection] = {
                                    "snapshot": snapshot_path,
                                    "status": "success",
                                }
                            else:
                                results["qdrant"][collection] = {
                                    "snapshot": None,
                                    "status": "failed",
                                }
                        except Exception as e:
                            results["qdrant"][collection] = {
                                "snapshot": None,
                                "status": "error",
                                "detail": str(e),
                            }
                            logger.error(
                                f"Qdrant snapshot failed for '{collection}': {e}",
                                exc_info=True,
                            )
                else:
                    results["qdrant"] = {
                        "status": "skipped",
                        "reason": "No collections found",
                    }
            else:
                results["qdrant"] = {
                    "status": "skipped",
                    "reason": "Qdrant not available",
                }
        except Exception as e:
            results["qdrant"] = {"status": "error", "detail": str(e)}
            results["errors"].append(f"Qdrant backup failed: {str(e)}")
            logger.error(f"Qdrant backup failed: {e}", exc_info=True)

        return {
            "status": "success" if not results["errors"] else "partial",
            "backup": results,
        }

    except Exception as e:
        logger.error(f"Backup endpoint crashed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "backup": results, "errors": [str(e)]},
        )


@app.get("/api/system/backups")
async def list_backups():
    """List all available backups."""
    backup_dir = PROJECT_ROOT / "backups"
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        return {"backups": []}

    backups = []
    for backup_file in sorted(backup_dir.glob("*.db"), reverse=True):
        backups.append(
            {
                "filename": backup_file.name,
                "size": backup_file.stat().st_size,
                "created": datetime.fromtimestamp(
                    backup_file.stat().st_mtime
                ).isoformat(),
            }
        )
    return {"backups": backups}


@app.post("/api/system/restore/{backup_filename}")
async def restore_backup(backup_filename: str, request: Request):
    """Restore SQLite database from backup."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    mgr = get_sqlite_manager()
    stored_key = mgr.get("api_key")
    if stored_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    backup_path = PROJECT_ROOT / "backups" / backup_filename
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")

    try:
        import shutil

        shutil.copy2(backup_path, DB_PATH)
        global sqlite_manager
        sqlite_manager = None
        return {
            "status": "success",
            "message": "Database restored. Restarting required.",
        }
    except Exception as e:
        logger.error(f"Restore failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings/system-prompt")
async def get_system_prompt_setting():
    """Get the current system prompt."""
    try:
        mgr = get_sqlite_manager()
        prompt = mgr.get("system_prompt")
        if not prompt:
            from app.agents.agent_core import DEFAULT_SYSTEM_PROMPT

            prompt = DEFAULT_SYSTEM_PROMPT
        return {"prompt": prompt}
    except Exception as e:
        logger.error(f"Failed to get system prompt: {e}")
        return {"prompt": ""}


@app.post("/api/settings/system-prompt")
async def save_system_prompt(request: dict, api_key: str = Depends(verify_api_key)):
    """Save the system prompt."""
    try:
        content = request.get("content", "")
        if not content.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        mgr = get_sqlite_manager()
        success = mgr.set("system_prompt", content)
        if success:
            logger.info(f"System prompt saved ({len(content)} chars)")
            return {"status": "saved"}
        raise RuntimeError("sqlite_manager.set() returned False")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save system prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings/heartbeat")
async def get_heartbeat_settings():
    """Get heartbeat interval settings (returns minutes)."""
    try:
        mgr = get_sqlite_manager()
        interval_seconds = mgr.get("heartbeat_interval")
        if interval_seconds:
            interval_minutes = int(interval_seconds) / 60
            return {
                "interval": interval_minutes,
                "interval_seconds": int(interval_seconds),
            }
        return {"interval": 5, "interval_seconds": 300}
    except Exception as e:
        logger.error(f"Failed to get heartbeat settings: {e}")
        return {"interval": 5, "interval_seconds": 300}


@app.post("/api/settings/heartbeat")
async def save_heartbeat_settings(request: dict):
    """Save heartbeat interval settings (in minutes)."""
    try:
        interval = request.get("interval", 5)
        if not isinstance(interval, (int, float)) or interval < 1:
            raise HTTPException(
                status_code=400, detail="Interval must be a number >= 1 minute"
            )

        interval_seconds = int(interval * 60)

        mgr = get_sqlite_manager()
        success = mgr.set("heartbeat_interval", str(interval_seconds))
        if success:
            logger.info(
                f"Heartbeat interval saved: {interval} minutes ({interval_seconds}s)"
            )
            return {
                "status": "saved",
                "interval": interval,
                "interval_seconds": interval_seconds,
            }
        raise RuntimeError("sqlite_manager.set() returned False")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save heartbeat settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings/heartbeat-prompt")
async def get_heartbeat_prompt():
    """Get the heartbeat system prompt."""
    try:
        mgr = get_sqlite_manager()
        prompt = mgr.get("heartbeat_prompt")
        if not prompt:
            prompt = """Quick system check. Respond with ONLY one of these:
- "OK" if everything is fine
- "ERROR: [brief description]" if something needs attention

Keep response under 20 words."""
        return {"prompt": prompt}
    except Exception as e:
        logger.error(f"Failed to get heartbeat prompt: {e}")
        return {"prompt": ""}


@app.post("/api/settings/heartbeat-prompt")
async def save_heartbeat_prompt(request: dict):
    """Save the heartbeat system prompt."""
    try:
        prompt = request.get("prompt", "")
        if not prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        mgr = get_sqlite_manager()
        success = mgr.set("heartbeat_prompt", prompt)
        if success:
            logger.info(f"Heartbeat prompt saved ({len(prompt)} chars)")
            return {"status": "saved"}
        raise RuntimeError("sqlite_manager.set() returned False")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save heartbeat prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings/system-prompt/default")
async def get_default_system_prompt():
    """Return the hardcoded default system prompt from agent_core.py."""
    from app.agents.agent_core import DEFAULT_SYSTEM_PROMPT

    return {"prompt": DEFAULT_SYSTEM_PROMPT}


@app.get("/api/settings/notifications")
async def get_notification_settings():
    """Get notification preferences."""
    try:
        mgr = get_sqlite_manager()
        intervals_json = mgr.get("notification_intervals")
        if intervals_json:
            return {"intervals": json.loads(intervals_json)}

        return {
            "intervals": [
                {"label": "24h", "minutes": 1440, "enabled": True},
                {"label": "1h", "minutes": 60, "enabled": True},
                {"label": "30m", "minutes": 30, "enabled": True},
                {"label": "15m", "minutes": 15, "enabled": True},
                {"label": "5m", "minutes": 5, "enabled": True},
                {"label": "0m", "minutes": 0, "enabled": True},
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get notification settings: {e}")
        return {"intervals": []}


@app.post("/api/settings/notifications")
async def save_notification_settings(request: dict):
    """Save notification preferences."""
    try:
        intervals = request.get("intervals", [])
        mgr = get_sqlite_manager()
        mgr.set("notification_intervals", json.dumps(intervals))
        return {"status": "saved"}
    except Exception as e:
        logger.error(f"Failed to save notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings/default-model")
async def get_default_model_setting():
    """Get the current default model."""
    try:
        mgr = get_sqlite_manager()
        model = mgr.get("default_model")
        return {"model": model or get_default_model()}
    except Exception as e:
        logger.error(f"Failed to get default model: {e}")
        return {"model": get_default_model()}


@app.post("/api/settings/default-model")
async def save_default_model_setting(request: dict):
    """Save the default model preference."""
    try:
        model = request.get("model", "")
        if not model:
            raise HTTPException(status_code=400, detail="Model name is required")

        mgr = get_sqlite_manager()
        success = mgr.set("default_model", model)
        if success:
            clear_model_cache()
            logger.info(f"Default model saved: {model}")
            return {"status": "saved", "model": model}
        raise RuntimeError("sqlite_manager.set() returned False")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save default model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prompts/{name}/versions")
async def list_prompt_versions(name: str):
    """List all versions of a prompt."""
    mgr = get_sqlite_manager()
    versions = mgr.list_prompt_versions(name)
    return {"versions": versions}


@app.post("/api/prompts/{name}/save")
async def save_prompt_version(
    name: str, request: dict, api_key: str = Depends(verify_api_key)
):
    """Save a new version of a prompt."""
    content = request.get("content", "")
    if not content.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    mgr = get_sqlite_manager()
    version_id = mgr.save_prompt_version(name, content)
    return {"status": "saved", "version_id": version_id}


@app.post("/api/prompts/{name}/rollback/{version}")
async def rollback_prompt_version(
    name: str, version: int, api_key: str = Depends(verify_api_key)
):
    """Rollback to a specific prompt version."""
    mgr = get_sqlite_manager()
    success = mgr.rollback_prompt(name, version)

    if success:
        clear_model_cache()  # Force reload
        return {"status": "success", "message": f"Rolled back to version {version}"}

    raise HTTPException(status_code=404, detail="Version not found")


# =============================================================================
# Authentication Endpoints
# =============================================================================


@app.get("/api/auth/status")
async def auth_status(request: Request):
    """Check if API key authentication is configured."""
    mgr = get_sqlite_manager()
    has_key = bool(mgr.get("api_key"))
    return {
        "enabled": has_key,
        "message": "API key authentication is active"
        if has_key
        else "No API key configured - system is open",
    }


@app.post("/api/auth/generate-key")
async def generate_new_api_key(request: Request):
    """Generate a new API key."""
    mgr = get_sqlite_manager()
    existing_key = mgr.get("api_key")

    if existing_key:
        await verify_api_key(request)

    new_key = generate_api_key()
    mgr.set("api_key", new_key)
    logger.info("New API key generated")

    return {
        "api_key": new_key,
        "message": "Save this key securely. It cannot be retrieved again.",
    }


@app.get("/api/auth/auto-key")
async def get_auto_generated_key():
    """Return the API key, generating one if missing."""
    mgr = get_sqlite_manager()
    key = mgr.get("api_key")

    # If no key exists, generate one
    if not key:
        from app.security.auth import generate_api_key

        key = generate_api_key()
        mgr.set("api_key", key)
        logger.info("Auto-generated new API key")
        return {"api_key": key, "auto_generated": True}


@app.delete("/api/auth/key")
async def revoke_api_key(request: Request):
    """Revoke the current API key (disables auth until new key generated)."""
    await verify_api_key(request)
    mgr = get_sqlite_manager()
    mgr.delete("api_key")
    logger.info("API key revoked")
    return {"status": "revoked", "message": "API key deleted. System is now open."}


# =============================================================================
# Heartbeat System
# =============================================================================


@app.post("/api/heartbeat/trigger")
async def trigger_heartbeat():
    """Manually trigger a quick heartbeat check."""
    try:
        logger.info("Manual heartbeat trigger requested")
        await run_heartbeat_check()
        return {
            "status": "success" if heartbeat_state["last_status"] == "OK" else "failed",
            "last_status": heartbeat_state["last_status"],
            "last_message": heartbeat_state["last_message"],
            "last_check": heartbeat_state["last_check"],
            "next_check": heartbeat_state.get("next_check"),
        }
    except Exception as e:
        logger.error(f"Manual heartbeat trigger error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


heartbeat_state = {
    "last_check": None,
    "last_status": "UNKNOWN",
    "last_message": "Not yet run",
    "next_check": None,
    "is_running": False,
}


async def check_and_dispatch_notifications():
    """Check due reminders/events and dispatch audio + toast notifications."""
    import sys

    mgr = get_sqlite_manager()

    intervals_json = mgr.get("notification_intervals")
    if not intervals_json:
        return

    try:
        intervals = json.loads(intervals_json)
        enabled_intervals = [i for i in intervals if i.get("enabled", True)]
    except Exception:
        return

    now = datetime.now()

    pending_reminders = mgr.get_pending_reminders(limit=50)
    for reminder in pending_reminders or []:
        try:
            due = datetime.fromisoformat(reminder.get("due_time", ""))
            delta = (due - now).total_seconds()

            if 0 <= delta <= 300:
                last_notified = mgr.get(f"notified_reminder_{reminder['id']}")
                if last_notified:
                    continue

                mgr.set(f"notified_reminder_{reminder['id']}", now.isoformat())

                await ws_manager.broadcast(
                    {
                        "type": "notification",
                        "notification_type": "reminder",
                        "title": "Reminder Due",
                        "message": reminder.get("text", ""),
                        "priority": reminder.get("priority", "medium"),
                        "audio": True,
                        "timestamp": now.isoformat(),
                    }
                )
                print(
                    f"    NOTIFICATION: Reminder dispatched: {reminder.get('text')}",
                    file=sys.stderr,
                    flush=True,
                )
        except Exception as e:
            logger.debug(f"Notification check failed for reminder: {e}")

    upcoming_events = mgr.get_upcoming_events(limit=20)
    for event in upcoming_events or []:
        try:
            start = datetime.fromisoformat(event.get("start_time", ""))
            delta = (start - now).total_seconds()

            for interval in enabled_intervals:
                minutes = interval.get("minutes", 0)
                window_start = minutes * 60
                window_end = max(0, window_start - 300)

                if window_end <= delta <= window_start:
                    notif_key = f"notified_event_{event['id']}_{minutes}m"
                    last_notified = mgr.get(notif_key)
                    if last_notified:
                        continue

                    mgr.set(notif_key, now.isoformat())

                    await ws_manager.broadcast(
                        {
                            "type": "notification",
                            "notification_type": "event",
                            "title": f"Upcoming: {interval['label']}",
                            "message": event.get("title", ""),
                            "priority": "medium",
                            "audio": minutes <= 15,
                            "timestamp": now.isoformat(),
                        }
                    )
                    print(
                        f"    NOTIFICATION: Event alert ({interval['label']}): {event.get('title')}",
                        file=sys.stderr,
                        flush=True,
                    )
                    break
        except Exception as e:
            logger.debug(f"Notification check failed for event: {e}")


async def run_heartbeat_check():
    """Execute a quick heartbeat check - SQLite connectivity + Notification Dispatch."""
    global heartbeat_state

    if heartbeat_state["is_running"]:
        logger.warning("Heartbeat already running, skipping")
        return

    if shutdown_flag:
        logger.info("Shutdown in progress, skipping heartbeat")
        return

    heartbeat_state["is_running"] = True
    heartbeat_state["last_status"] = "RUNNING"
    heartbeat_state["last_message"] = "Checking database..."
    logger.info("Starting quick heartbeat check...")

    try:
        mgr = get_sqlite_manager()
        test_read = mgr.get("last_heartbeat")
        test_key = f"__heartbeat_test_{datetime.now().timestamp()}"
        mgr.set(test_key, "ok")
        mgr.delete(test_key)

        heartbeat_state["last_check"] = datetime.now().isoformat()
        heartbeat_state["last_status"] = "OK"
        heartbeat_state[
            "last_message"
        ] = f"Database healthy (checked at {datetime.now().strftime('%H:%M:%S')})"
        logger.info(
            f"Heartbeat check completed (SQLite OK) at {datetime.now().strftime('%H:%M:%S')}"
        )

        mgr.set("last_heartbeat", heartbeat_state["last_check"])
        mgr.set("last_heartbeat_status", heartbeat_state["last_status"])
        mgr.set("last_heartbeat_message", heartbeat_state["last_message"])

    except Exception as e:
        heartbeat_state["last_check"] = datetime.now().isoformat()
        heartbeat_state["last_status"] = "ERROR"
        heartbeat_state["last_message"] = f"Database error: {str(e)}"
        logger.error(f"Heartbeat check failed: {e}", exc_info=True)

        try:
            mgr = get_sqlite_manager()
            mgr.set("last_heartbeat", heartbeat_state["last_check"])
            mgr.set("last_heartbeat_status", heartbeat_state["last_status"])
            mgr.set("last_heartbeat_message", heartbeat_state["last_message"])
        except Exception:
            pass

    finally:
        heartbeat_state["is_running"] = False
        await update_next_check_time()
        logger.debug(
            f"Next check scheduled for: {heartbeat_state.get('next_check', 'unknown')}"
        )

        try:
            await check_and_dispatch_notifications()
        except Exception as e:
            logger.debug(f"Notification dispatch error: {e}")

        try:
            await ws_manager.broadcast(
                {
                    "type": "heartbeat",
                    "status": heartbeat_state["last_status"],
                    "message": heartbeat_state["last_message"],
                    "last_check": heartbeat_state["last_check"],
                    "next_check": heartbeat_state.get("next_check"),
                }
            )
        except Exception as e:
            logger.debug(f"Failed to broadcast heartbeat: {e}")

        try:
            mgr = get_sqlite_manager()
            last_qdrant_backup = mgr.get("last_qdrant_backup")
            now = datetime.now()

            should_backup = False
            if not last_qdrant_backup:
                should_backup = True
            else:
                last_dt = datetime.fromisoformat(last_qdrant_backup)
                if (now - last_dt).days >= 7:
                    should_backup = True

            if should_backup:
                qm = get_qdrant_manager()
                if qm.qdrant_available:
                    qm.backup_all_collections(keep=7)
                    mgr.set("last_qdrant_backup", now.isoformat())
                    logger.info("Weekly Qdrant backup completed")
        except Exception as e:
            logger.debug(f"Weekly Qdrant backup check skipped: {e}")


async def update_next_check_time():
    """Calculate and store the next check time."""
    global heartbeat_state

    if heartbeat_state["is_running"]:
        heartbeat_state["next_check"] = None
        return

    try:
        mgr = get_sqlite_manager()
        interval_seconds = mgr.get("heartbeat_interval")

        if interval_seconds:
            interval_seconds = int(interval_seconds)
            if heartbeat_state["last_check"]:
                last_check = datetime.fromisoformat(heartbeat_state["last_check"])
                next_check = last_check + timedelta(seconds=interval_seconds)
                heartbeat_state["next_check"] = next_check.isoformat()
            else:
                next_check = datetime.now() + timedelta(seconds=interval_seconds)
                heartbeat_state["next_check"] = next_check.isoformat()
        else:
            next_check = datetime.now() + timedelta(seconds=300)
            heartbeat_state["next_check"] = next_check.isoformat()
    except Exception as e:
        logger.warning(f"Failed to update next check time: {e}")


async def heartbeat_scheduler():
    """Background task that runs heartbeat checks at configured intervals."""
    global shutdown_flag
    logger.info("Heartbeat scheduler started")

    await run_heartbeat_check()

    while not shutdown_flag:
        try:
            mgr = get_sqlite_manager()
            interval_seconds = mgr.get("heartbeat_interval")

            if not interval_seconds:
                interval_seconds = 300

            interval_seconds = int(interval_seconds)

            for _ in range(interval_seconds):
                if shutdown_flag:
                    logger.info("Heartbeat scheduler received shutdown signal")
                    return
                await asyncio.sleep(1)

            if not shutdown_flag:
                await run_heartbeat_check()

        except asyncio.CancelledError:
            logger.info("Heartbeat scheduler cancelled")
            return
        except Exception as e:
            logger.error(f"Heartbeat scheduler error: {e}", exc_info=True)
            await asyncio.sleep(60)


@app.get("/api/heartbeat/status")
async def get_heartbeat_status():
    """Get current heartbeat state."""
    global heartbeat_state
    return heartbeat_state


# =============================================================================
# Agent Endpoints
# =============================================================================


def _build_stm_context(query: str) -> str:
    """Build a concise STM context block for LLM injection based on query relevance."""
    import time

    start = time.time()
    mgr = get_sqlite_manager()
    sections = []

    # Load ALL user profile data (facts, patterns, notes)
    try:
        profile = mgr.get_user_profile()
        if profile:
            fact_lines = []
            note_lines = []
            pattern_lines = []

            for key, value in profile.items():
                if key.startswith("stm_note_"):
                    # These are direct notes from STM
                    if isinstance(value, str):
                        note_lines.append(f"- {value}")
                    continue

                if key.startswith("pattern_") or key.startswith("learned_pattern_"):
                    # These are learned patterns
                    if isinstance(value, str):
                        try:
                            pattern_data = json.loads(value)
                            if isinstance(pattern_data, dict):
                                desc = pattern_data.get(
                                    "description", pattern_data.get("preference", "")
                                )
                                if desc:
                                    pattern_lines.append(f"- {desc}")
                        except:
                            pass
                    continue

                if key == "api_key_retrieved":
                    continue

                # Regular user facts
                if isinstance(value, str):
                    try:
                        fact_data = json.loads(value)
                        if isinstance(fact_data, dict):
                            if fact_data.get("type") == "user_fact":
                                fact_lines.append(
                                    f"- {fact_data.get('raw', fact_data.get('description', value))}"
                                )
                            elif "description" in fact_data:
                                fact_lines.append(f"- {fact_data['description']}")
                            elif "preference" in fact_data:
                                fact_lines.append(f"- {fact_data['preference']}")
                            continue
                    except (json.JSONDecodeError, TypeError):
                        pass
                    fact_lines.append(f"- {value}")

            if fact_lines:
                sections.append("### Personal Facts\n" + "\n".join(fact_lines[:10]))
            if note_lines:
                sections.append("### User Notes\n" + "\n".join(note_lines[:5]))
            if pattern_lines:
                sections.append(
                    "### Learned Preferences\n" + "\n".join(pattern_lines[:5])
                )
    except Exception as e:
        logger.debug(f"Failed to load user profile for context: {e}")

    # Time-based context (existing logic)
    lower_q = query.lower()
    time_keywords = [
        "appointment",
        "schedule",
        "meeting",
        "birthday",
        "deadline",
        "when",
        "next",
        "upcoming",
        "last",
        "dentist",
        "doctor",
    ]

    if any(kw in lower_q for kw in time_keywords):
        try:
            events = mgr.get_upcoming_events(limit=5)
            if events:
                event_lines = []
                for ev in events:
                    title = ev.get("title", "")
                    start_time = ev.get("start_time", "")
                    event_lines.append(f"- {title} on {start_time}")
                sections.append("### Upcoming Events\n" + "\n".join(event_lines))
        except Exception:
            pass

        try:
            reminders = mgr.get_pending_reminders(limit=5)
            if reminders:
                reminder_lines = []
                for rem in reminders:
                    text = rem.get("text", "")
                    due = rem.get("due_time", "")
                    reminder_lines.append(f"- {text} (due: {due})")
                sections.append("### Active Reminders\n" + "\n".join(reminder_lines))
        except Exception:
            pass

    task_keywords = ["todo", "task", "done", "finish", "complete", "pending"]
    if any(kw in lower_q for kw in task_keywords):
        try:
            todos = mgr.get_pending_todos(limit=5)
            if todos:
                todo_lines = []
                for td in todos:
                    title = td.get("title", "")
                    priority = td.get("priority", "")
                    todo_lines.append(f"- [{priority}] {title}")
                sections.append("### Pending Todos\n" + "\n".join(todo_lines))
        except Exception:
            pass

    result = "\n\n".join(sections) if sections else ""
    elapsed = time.time() - start
    logger.info(f"STM context built in {elapsed:.3f}s, length: {len(result)} chars")
    return result


def detect_repetition(text: str, threshold: int = 5) -> bool:
    """Detect if text contains repetitive loops."""
    lines = text.split("\n")
    if len(lines) < 10:
        return False

    paragraph_counts = {}
    for i in range(0, len(lines) - 2):
        paragraph = "\n".join(lines[i : i + 3])
        paragraph_counts[paragraph] = paragraph_counts.get(paragraph, 0) + 1

    return any(count >= threshold for count in paragraph_counts.values())


@app.post("/api/chat")
async def chat_endpoint(request: Request, chat_request: AgentRequest):
    """Chat endpoint with file creation support and STM context injection."""
    try:
        import time as _time

        _model_start = _time.time()
        loop = asyncio.get_event_loop()

        def run_chat():
            t0 = _time.time()

            # Direct model usage - NO ROUTING OVERHEAD
            requested_model = chat_request.model or get_default_model()

            # =================================================================
            # FILE CREATION DETECTION - Check for [FILE] prefix
            # =================================================================
            query_text = chat_request.query
            extracted_filename = None

            if query_text.strip().startswith("[FILE]"):
                # Extract filename from query
                # Pattern: [FILE] Write something to filename.ext
                import re

                match = re.search(r"\[FILE\].*?(\w+\.\w+)", query_text)
                if match:
                    extracted_filename = match.group(1)
                    # Remove [FILE] prefix from query for processing
                    query_text = query_text.replace("[FILE]", "").strip()
                    logger.info(f"[CHAT] File creation requested: {extracted_filename}")

                    # Route to process_request for file creation
                    try:
                        result = process_request(
                            user_query=query_text,
                            filename=extracted_filename,
                            model=requested_model,
                        )

                        # Ensure result has content field
                        if "content" not in result or not result["content"]:
                            result["content"] = result.get(
                                "message", "File creation completed."
                            )

                        return result
                    except Exception as file_err:
                        logger.error(
                            f"[CHAT] File creation failed: {file_err}", exc_info=True
                        )
                        return {
                            "content": f"File creation failed: {str(file_err)}",
                            "model": requested_model,
                            "warning": "File creation error",
                        }

            # =================================================================
            # SQL QUERY DETECTION - Route to codeqwen for SQL
            # =================================================================
            query_lower = query_text.lower()
            sql_keywords = [
                "select",
                "show",
                "list",
                "find",
                "count",
                "what are my",
                "show my",
            ]

            if (
                any(kw in query_lower for kw in sql_keywords)
                and "codeqwen" not in requested_model
            ):
                requested_model = "codeqwen:7b"
                logger.info(f"[CHAT] SQL query detected, using {requested_model}")

            try:
                resolved_model = model_manager.resolve_model(requested_model)
            except RuntimeError:
                resolved_model = get_default_model()

            t1 = _time.time()
            logger.info(f"[CHAT] Model resolved in {t1-t0:.3f}s: {resolved_model}")

            llm = _get_llm(resolved_model)
            t2 = _time.time()
            logger.info(
                f"[CHAT] LLM instance ready in {t2-t1:.3f}s (includes Ollama load if cold)"
            )

            stm_context = _build_stm_context(query_text)
            t3 = _time.time()
            logger.info(
                f"[CHAT] STM context built in {t3-t2:.3f}s ({len(stm_context)} chars)"
            )

            base_prompt = get_system_prompt()
            full_prompt = (
                f"{base_prompt}\n\n## User's Personal Context (from Short-Term Memory)\n{stm_context}\n\nUser: {query_text}\nAssistant:"
                if stm_context
                else f"{base_prompt}\n\nUser: {query_text}\nAssistant:"
            )

            t4 = _time.time()
            logger.info(
                f"[CHAT] Prompt assembled in {t4-t3:.3f}s ({len(full_prompt)} tokens est.)"
            )

            response = llm.invoke(full_prompt)

            try:
                prompt_tokens = len(full_prompt) // 4
                completion_tokens = len(response.content) // 4
                mgr = get_sqlite_manager()
                mgr.track_token_usage(
                    resolved_model, prompt_tokens, completion_tokens, "chat"
                )
            except Exception as e:
                logger.debug(f"Token tracking failed: {e}")

            if detect_repetition(response.content):
                logger.warning(f"[CHAT] Repetition loop detected from {resolved_model}")
                try:
                    logger.info(
                        f"[CHAT] Retrying with higher temperature (0.9, repeat_penalty=1.5)"
                    )
                    llm_retry = _get_llm(
                        resolved_model, temperature=0.9, repeat_penalty=1.5
                    )
                    response = llm_retry.invoke(full_prompt)

                    if detect_repetition(response.content):
                        logger.error(
                            f"[CHAT] Retry also failed - model {resolved_model} inadequate"
                        )
                        return {
                            "content": INADEQUATE_MODEL_RESPONSE,
                            "model": resolved_model,
                            "warning": "Model entered repetition loop even after retry",
                        }
                    else:
                        logger.info(f"[CHAT] Retry succeeded")
                except Exception as retry_err:
                    logger.error(f"[CHAT] Retry failed: {retry_err}")
                    return {
                        "content": INADEQUATE_MODEL_RESPONSE,
                        "model": resolved_model,
                        "warning": f"Retry failed: {str(retry_err)}",
                    }

            t5 = _time.time()
            logger.info(f"[CHAT] LLM generation completed in {t5-t4:.3f}s")

            return {"content": response.content, "model": resolved_model}

        result = await loop.run_in_executor(executor, run_chat)

        _model_duration = _time.time() - _model_start
        resolved = result.get("model", get_default_model())
        MODEL_REQUEST_COUNT.labels(model=resolved, endpoint="chat").inc()
        MODEL_DURATION.labels(model=resolved).observe(_model_duration)

        return result
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SQLite Memory Endpoints
# =============================================================================


@app.delete("/api/memory/sqlite/chat/thread/{thread_id}")
async def delete_chat_thread(thread_id: str, api_key: str = Depends(verify_api_key)):
    """Delete a chat thread and all its messages."""
    try:
        mgr = get_sqlite_manager()
        with mgr.get_cursor() as cur:
            cur.execute("DELETE FROM chat_messages WHERE thread_id = ?", (thread_id,))
            cur.execute("DELETE FROM chat_threads WHERE id = ?", (thread_id,))
        logger.info(f"Deleted chat thread: {thread_id}")
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete chat thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/sqlite/chat/threads")
@limiter.limit("60/minute")
async def get_chat_threads(request: Request):
    try:
        mgr = get_sqlite_manager()
        with mgr.get_cursor() as cur:
            cur.execute(
                "SELECT id, title, created_at, last_message_at FROM chat_threads ORDER BY created_at DESC"
            )
            threads = [
                {
                    "id": row[0],
                    "title": row[1],
                    "created_at": row[2],
                    "last_message_at": row[3],
                }
                for row in cur.fetchall()
            ]
        return {"threads": threads}
    except Exception as e:
        logger.error(f"Failed to get chat threads: {e}", exc_info=True)
        return {"threads": []}


@app.get("/api/memory/sqlite/chat/messages/{thread_id}")
async def get_chat_messages(thread_id: str):
    try:
        mgr = get_sqlite_manager()
        with mgr.get_cursor() as cur:
            cur.execute(
                """
                SELECT id, role, content, timestamp, model, filename
                FROM chat_messages
                WHERE thread_id = ?
                ORDER BY timestamp ASC
            """,
                (thread_id,),
            )
            messages = []
            for row in cur.fetchall():
                timestamp = 0
                if row[3]:
                    try:
                        dt_str = str(row[3]).replace(" ", "T")
                        dt = datetime.fromisoformat(dt_str)
                        timestamp = int(dt.timestamp() * 1000)
                    except Exception:
                        pass

                messages.append(
                    {
                        "id": row[0],
                        "from": "ai" if row[1] == "assistant" else row[1],
                        "text": row[2],
                        "timestamp": timestamp,
                        "model": row[4],
                        "filename": row[5],
                    }
                )
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}", exc_info=True)
        return {"messages": []}


@app.get("/api/memory/sqlite/notifications/due-soon")
async def get_due_soon_notifications():
    """Fetch upcoming events and pending reminders."""
    try:
        mgr = get_sqlite_manager()
        events = mgr.get_upcoming_events(limit=15)
        reminders = mgr.get_pending_reminders(limit=15)

        logger.info(
            f"Notification check: {len(events)} events, {len(reminders)} reminders"
        )

        return {
            "events": events or [],
            "reminders": reminders or [],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Critical error in notifications endpoint: {e}", exc_info=True)
        return {
            "events": [],
            "reminders": [],
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/memory/sqlite/events/upcoming")
@limiter.limit("60/minute")
async def get_upcoming_events(request: Request, limit: int = 20):
    """Get upcoming events."""
    try:
        mgr = get_sqlite_manager()
        events = mgr.get_upcoming_events(limit=limit)
        return {"events": events or []}
    except Exception as e:
        logger.error(f"Failed to get upcoming events: {e}")
        return {"events": []}


@app.post("/api/memory/sqlite/events")
@limiter.limit("30/minute")
async def create_or_update_event(request: Request, event_request: EventRequest):
    """Create or update an event."""
    try:
        mgr = get_sqlite_manager()
        event_data = event_request.model_dump(exclude_none=True)
        event_id = mgr.save_event(event_data)
        return {"status": "saved", "id": event_id}
    except Exception as e:
        logger.error(f"Failed to save event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/memory/sqlite/events/{event_id}")
async def delete_event(event_id: str, api_key: str = Depends(verify_api_key)):
    """Delete an event."""
    try:
        mgr = get_sqlite_manager()
        mgr.delete_event(event_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/sqlite/reminders/upcoming")
async def get_upcoming_reminders(limit: int = 20):
    """Get upcoming reminders."""
    try:
        mgr = get_sqlite_manager()
        reminders = mgr.get_pending_reminders(limit=limit)
        return {"reminders": reminders or []}
    except Exception as e:
        logger.error(f"Failed to get reminders: {e}")
        return {"reminders": []}


@app.post("/api/memory/sqlite/reminders")
@limiter.limit("30/minute")
async def create_or_update_reminder(
    request: Request, reminder_request: ReminderRequest
):
    """Create or update a reminder."""
    try:
        mgr = get_sqlite_manager()
        reminder_data = reminder_request.model_dump(exclude_none=True)
        reminder_id = mgr.save_reminder(reminder_data)
        return {"status": "saved", "id": reminder_id}
    except Exception as e:
        logger.error(f"Failed to save reminder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/memory/sqlite/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    """Delete a reminder and all its recurring instances."""
    try:
        mgr = get_sqlite_manager()

        with mgr.get_cursor() as cur:
            if "_" in reminder_id:
                base_id = reminder_id.rsplit("_", 1)[0]
                cur.execute("DELETE FROM reminders WHERE id LIKE ?", (f"{base_id}_%",))
                cur.execute("DELETE FROM reminders WHERE id = ?", (base_id,))
                deleted_count = cur.rowcount
            else:
                cur.execute(
                    "DELETE FROM reminders WHERE id = ? OR id LIKE ?",
                    (reminder_id, f"{reminder_id}_%"),
                )
                deleted_count = cur.rowcount

        logger.info(f"Deleted {deleted_count} reminder(s) with ID: {reminder_id}")
        return {"status": "deleted", "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Failed to delete reminder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/sqlite/todos")
async def get_todos(limit: int = 50):
    """Get all todos."""
    try:
        mgr = get_sqlite_manager()
        todos = mgr.get_pending_todos(limit=limit)
        return {"todos": todos or []}
    except Exception as e:
        logger.error(f"Failed to get todos: {e}")
        return {"todos": []}


@app.post("/api/memory/sqlite/todos")
@limiter.limit("30/minute")
async def create_or_update_todo(request: Request, todo_request: TodoRequest):
    """Create or update a todo."""
    try:
        mgr = get_sqlite_manager()
        todo_data = todo_request.model_dump(exclude_none=True)
        todo_id = mgr.save_todo(todo_data)
        return {"status": "saved", "id": todo_id}
    except Exception as e:
        logger.error(f"Failed to save todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/memory/sqlite/todos/{todo_id}")
async def delete_todo(todo_id: str, api_key: str = Depends(verify_api_key)):
    """Delete a todo."""
    try:
        mgr = get_sqlite_manager()
        mgr.delete_todo(todo_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/sqlite/chat/thread")
async def save_chat_thread(request: Request, api_key: str = Depends(verify_api_key)):
    """Save or update a chat thread."""
    try:
        data = await request.json()
        thread_id = data.get("id")
        title = data.get("title", "New Chat")

        if not thread_id:
            raise HTTPException(status_code=400, detail="Thread ID required")

        mgr = get_sqlite_manager()
        with mgr.get_cursor() as cur:
            cur.execute(
                """
                INSERT OR REPLACE INTO chat_threads (id, title, created_at, last_message_at)
                VALUES (?, ?, COALESCE((SELECT created_at FROM chat_threads WHERE id = ?), CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)
            """,
                (thread_id, title, thread_id),
            )

        return {"status": "saved", "thread_id": thread_id}
    except Exception as e:
        logger.error(f"Failed to save chat thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/sqlite/chat/message")
async def save_chat_message(request: Request, api_key: str = Depends(verify_api_key)):
    """Save a chat message."""
    try:
        data = await request.json()
        thread_id = data.get("thread_id")
        role = data.get("role")
        content = data.get("content")
        model = data.get("model", "unknown")
        timestamp = data.get("timestamp")

        if not all([thread_id, role, content]):
            raise HTTPException(
                status_code=400, detail="thread_id, role, and content required"
            )

        mgr = get_sqlite_manager()
        with mgr.get_cursor() as cur:
            # Generate message ID
            import uuid

            msg_id = str(uuid.uuid4())

            cur.execute(
                """
                INSERT INTO chat_messages (id, thread_id, role, content, model, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    msg_id,
                    thread_id,
                    role,
                    content,
                    model,
                    timestamp or datetime.now().isoformat(),
                ),
            )

            # Update thread's last_message_at
            cur.execute(
                """
                UPDATE chat_threads SET last_message_at = CURRENT_TIMESTAMP WHERE id = ?
            """,
                (thread_id,),
            )

        return {"status": "saved", "message_id": msg_id}
    except Exception as e:
        logger.error(f"Failed to save chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/usage/tokens")
async def get_token_usage(days: int = 7):
    """Get token usage statistics."""
    mgr = get_sqlite_manager()
    summary = mgr.get_token_usage_summary(days)

    total_tokens = sum(item["total_tokens"] for item in summary)
    total_requests = sum(item["requests"] for item in summary)

    return {
        "summary": summary,
        "totals": {
            "tokens": total_tokens,
            "requests": total_requests,
            "avg_tokens_per_request": total_tokens / total_requests
            if total_requests > 0
            else 0,
        },
    }


# =============================================================================
# STM Quick-Entry with LLM Parsing (codeqwen:7b)
# =============================================================================


def get_stm_schema_context() -> str:
    """Get the complete STM database schema for SQL generation."""
    return """
Database: SQLite
Tables:
1. chat_threads (id TEXT PRIMARY KEY, title TEXT, created_at DATETIME, last_message_at DATETIME)
2. chat_messages (id TEXT PRIMARY KEY, thread_id TEXT, role TEXT, content TEXT, timestamp DATETIME, model TEXT)
3. reminders (id TEXT PRIMARY KEY, text TEXT, due_time TEXT, priority TEXT, completed BOOLEAN, created_at DATETIME, alert_type TEXT, alert_sound TEXT)
4. events (id TEXT PRIMARY KEY, title TEXT, description TEXT, start_time TEXT, end_time TEXT, category TEXT, is_recurring BOOLEAN, recurrence_type TEXT, recurrence_days TEXT, recurrence_end_date TEXT)
5. todos (id TEXT PRIMARY KEY, title TEXT, description TEXT, priority TEXT, completed BOOLEAN, due_date TEXT, created_at DATETIME)
6. user_profile (key TEXT PRIMARY KEY, value TEXT, updated_at DATETIME)
7. notes (id TEXT PRIMARY KEY, title TEXT, content TEXT, created_at DATETIME, updated_at DATETIME)

Relationships:
- chat_messages.thread_id → chat_threads.id
- All timestamps are ISO format (YYYY-MM-DDTHH:MM:SS)
- Boolean fields use 0/1 (SQLite)
- Priority values: 'low', 'medium', 'high'
- Category values: 'general', 'appointment', 'reminder', 'work', 'personal'
"""


def parse_stm_with_regex(text: str) -> Optional[dict]:
    """Fast regex-based parsing for simple patterns. Returns None if no match."""
    text_lower = text.lower()

    # Pattern: "My favorite X is Y" / "I like X" / "I prefer X"
    favorite_patterns = [
        r"my\s+favorite\s+(\w+)\s+is\s+(.+)",
        r"i\s+(?:like|love|prefer)\s+(.+)",
        r"(\w+)\s+is\s+my\s+favorite",
    ]

    for pattern in favorite_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if len(match.groups()) == 2:
                category, value = match.groups()
            else:
                value = match.group(1)
                category = "preference"

            return {
                "intent": "note",
                "text": text,
                "pattern_learned": True,
                "pattern_description": f"User {category}: {value.strip()}",
                "due_time": None,
                "recurrence": None,
                "priority": "medium",
            }

    # Pattern: Simple reminders "remind me to X"
    reminder_match = re.search(
        r"remind\s+me\s+(?:to\s+)?(.+?)(?:\s+in\s+(\d+)\s+(minute|hour|day)s?)?$",
        text_lower,
    )
    if reminder_match:
        reminder_text = reminder_match.group(1).strip()
        time_value = reminder_match.group(2)
        time_unit = reminder_match.group(3)

        due_time = datetime.now()
        if time_value and time_unit:
            if time_unit == "minute":
                due_time += timedelta(minutes=int(time_value))
            elif time_unit == "hour":
                due_time += timedelta(hours=int(time_value))
            elif time_unit == "day":
                due_time += timedelta(days=int(time_value))

        return {
            "intent": "reminder",
            "text": reminder_text,
            "due_time": due_time.isoformat(),
            "recurrence": None,
            "priority": "medium",
            "pattern_learned": False,
        }

    return None  # No regex match, fall back to LLM


def parse_stm_with_llm(text: str) -> dict:
    """Parse STM with regex fast-path, then codeqwen:7b fallback."""

    # Try regex first (instant)
    regex_result = parse_stm_with_regex(text)
    if regex_result:
        logger.info(f"Parsed with regex (instant): {regex_result}")
        return regex_result

    # Fall back to codeqwen:7b with JSON parsing (~10 seconds)
    logger.info(f"Regex failed, using codeqwen:7b for JSON parsing...")

    try:
        llm = _get_llm("codeqwen:7b", temperature=0.3, num_predict=1024)

        prompt = f"""You are a personal assistant that parses natural language into structured actions.

Current time: {datetime.now().isoformat()}

Parse this request and return ONLY valid JSON with these fields:
- "intent": one of ["reminder", "event", "todo", "note"]
- "text": the main content/message
- "due_time": ISO timestamp for when this is due (calculate from "in X minutes", "at 3pm", etc.)
- "recurrence": null, or one of ["every_minute", "every_5min", "every_15min", "every_30min", "every_hour", "daily", "weekly"]
- "duration_minutes": how long the recurrence should last (null if not recurring)
- "priority": "low", "medium", or "high"
- "due_date": ISO date for todos (null if not applicable)
- "alert_type": "sound" or "visual" (default "sound" if user says "alert")
- "alert_sound": filename like "notification.mp3" (default "notification.mp3")
- "pattern_learned": boolean - true if this reveals a user habit/preference
- "pattern_description": if pattern_learned is true, describe the pattern

Rules:
- If user says "alert" or "sound", set alert_type="sound"
- If user says "remind me every minute for 10 minutes", set recurrence="every_minute", duration_minutes=10
- Recurrence starts NOW, not at the event time
- If user says "appointment in 10 min", set due_time to current_time + 10 minutes
- If user says "at 3pm", set due_time to today at 15:00
- If no time specified, set due_time to 30 minutes from now
- If this reveals a preference (like always wanting sound alerts), set pattern_learned=true
- Return ONLY the JSON object, no explanations

Request: "{text}"

JSON:"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        logger.info(f"=== CODEQWEN RAW RESPONSE ===\n{content}\n=== END ===")

        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            parsed = json.loads(json_match.group(0))
            logger.info(
                f"=== PARSED JSON ===\n{json.dumps(parsed, indent=2)}\n=== END ==="
            )
            return parsed

        logger.warning(f"codeqwen:7b returned invalid JSON: {content}")
        return None
    except Exception as e:
        logger.error(f"codeqwen:7b parsing failed: {e}", exc_info=True)
        return None


def generate_sql_from_natural_language(user_query: str) -> str:
    """Convert natural language to SQL using codeqwen:7b ONLY (no validation overhead)."""

    schema_context = get_stm_schema_context()

    few_shot_examples = """
Examples:
User: "Show my upcoming reminders"
SQL: SELECT * FROM reminders WHERE completed = 0 AND due_time > datetime('now') ORDER BY due_time ASC;

User: "What events do I have this week?"
SQL: SELECT * FROM events WHERE start_time >= datetime('now') AND start_time <= datetime('now', '+7 days') ORDER BY start_time ASC;

User: "Find all my chat messages about Python"
SQL: SELECT * FROM chat_messages WHERE content LIKE '%Python%' ORDER BY timestamp DESC;

User: "Show my incomplete todos sorted by priority"
SQL: SELECT * FROM todos WHERE completed = 0 ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, due_date ASC;

User: "Count how many messages I sent today"
SQL: SELECT COUNT(*) as message_count FROM chat_messages WHERE role = 'user' AND date(timestamp) = date('now');
"""

    prompt = f"""You are an expert SQL developer. Convert the user's natural language request into a valid SQLite SQL query.

{schema_context}

{few_shot_examples}

Rules:
- Generate ONLY the SQL query, no explanations
- Use proper SQLite syntax
- Always include WHERE clauses to filter appropriately
- Use ORDER BY for sorted results
- Use LIMIT for large result sets
- Handle date/time comparisons correctly with datetime() functions
- Return only executable SQL

User Request: "{user_query}"

SQL:"""

    try:
        llm = _get_llm("codeqwen:7b", temperature=0.1, num_predict=512)
        response = llm.invoke(prompt)

        sql = response.content.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()

        # Safety checks
        if not sql.upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
            logger.warning(f"Generated invalid SQL: {sql}")
            return None

        if "DROP" in sql.upper() or "TRUNCATE" in sql.upper():
            logger.warning(f"Dangerous SQL blocked: {sql}")
            return None

        return sql
    except Exception as e:
        logger.error(f"SQL generation failed: {e}", exc_info=True)
        return None


@app.post("/api/memory/stm/quick-entry")
async def stm_quick_entry(request: dict, api_key: str = Depends(verify_api_key)):
    """Parse natural language into structured reminders/events/todos using regex + codeqwen:7b."""
    try:
        text = request.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        # Parse with regex (instant) or codeqwen:7b (~10s)
        parsed = parse_stm_with_llm(text)

        if not parsed:
            logger.error(f"LLM returned None for: {text}")
            raise HTTPException(status_code=400, detail="Failed to parse request")

        if "intent" not in parsed:
            logger.error(f"Missing intent in parsed result: {parsed}")
            raise HTTPException(status_code=400, detail="Could not determine intent")

        intent = parsed["intent"]
        mgr = get_sqlite_manager()

        # Pattern learning (already extracted by parser)
        pattern_learned = parsed.get("pattern_learned", False)
        pattern_description = parsed.get("pattern_description", "")
        alert_type = parsed.get("alert_type", "sound")
        alert_sound = parsed.get("alert_sound", "notification.mp3")

        if pattern_learned and pattern_description:
            pattern_key = f"pattern_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            pattern_data = {
                "description": pattern_description,
                "alert_type": alert_type,
                "alert_sound": alert_sound,
                "learned_at": datetime.now().isoformat(),
            }
            mgr.save_user_profile(pattern_key, json.dumps(pattern_data))
            logger.info(f"Learned user pattern: {pattern_description}")

        if intent == "reminder":
            reminder_text = parsed.get("text", text)
            due_time_str = parsed.get("due_time")
            recurrence = parsed.get("recurrence")
            duration_minutes = parsed.get("duration_minutes")
            priority = parsed.get("priority", "medium")

            # Parse due_time
            if due_time_str:
                try:
                    due_time = datetime.fromisoformat(
                        due_time_str.replace("Z", "+00:00")
                    )
                except:
                    due_time = datetime.now() + timedelta(minutes=30)
            else:
                due_time = datetime.now() + timedelta(minutes=30)

            # Handle recurrence - START FROM NOW
            if recurrence and duration_minutes:
                interval_map = {
                    "every_minute": 1,
                    "every_5min": 5,
                    "every_15min": 15,
                    "every_30min": 30,
                    "every_hour": 60,
                }

                if recurrence in interval_map:
                    interval_minutes = interval_map[recurrence]
                    base_time = datetime.now()
                    num_instances = int(duration_minutes) // interval_minutes

                    for i in range(num_instances):
                        instance_time = base_time + timedelta(
                            minutes=i * interval_minutes
                        )
                        instance_id = (
                            f"reminder_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}"
                        )

                        instance_data = {
                            "text": reminder_text,
                            "due_time": instance_time.isoformat(),
                            "priority": priority,
                            "completed": False,
                        }
                        mgr.save_reminder({**instance_data, "id": instance_id})

                    return {
                        "status": "success",
                        "intent": "reminder",
                        "message": f"Created {num_instances} alerts every {interval_minutes} minute(s)",
                        "id": instance_id,
                    }

            # Single reminder
            reminder_data = {
                "text": reminder_text,
                "due_time": due_time.isoformat(),
                "priority": priority,
                "completed": False,
            }

            reminder_id = mgr.save_reminder(reminder_data)

            return {
                "status": "success",
                "intent": "reminder",
                "message": f"Reminder created: '{reminder_text}' (due: {due_time.isoformat()[:16]})",
                "id": reminder_id,
            }

        elif intent == "event":
            event_data = {
                "title": parsed.get("text", text),
                "start_time": parsed.get("due_time", datetime.now().isoformat()),
                "category": "appointment",
                "is_recurring": False,
            }
            event_id = mgr.save_event(event_data)
            return {
                "status": "success",
                "intent": "event",
                "message": f"Event scheduled: '{event_data['title']}'",
                "id": event_id,
            }

        elif intent == "todo":
            todo_data = {
                "title": parsed.get("text", text),
                "due_date": parsed.get("due_date"),
                "priority": parsed.get("priority", "medium"),
                "completed": False,
            }
            todo_id = mgr.save_todo(todo_data)
            return {
                "status": "success",
                "intent": "todo",
                "message": f"Todo created: '{todo_data['title']}'",
                "id": todo_id,
            }

        else:  # note or unknown
            note_key = f"stm_note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            mgr.save_user_profile(note_key, text)
            return {
                "status": "success",
                "intent": "note",
                "message": f"Saved to short-term memory: '{text[:80]}{'...' if len(text) > 80 else ''}'",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STM quick entry failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/sqlite/query")
async def execute_natural_language_query(
    request: dict, api_key: str = Depends(verify_api_key)
):
    """Execute a natural language query against the STM database using codeqwen:7b."""
    try:
        user_query = request.get("query", "").strip()
        if not user_query:
            raise HTTPException(status_code=400, detail="Query is required")

        # Generate SQL from natural language
        sql = generate_sql_from_natural_language(user_query)

        if not sql:
            return {
                "status": "error",
                "message": "Could not generate valid SQL from your request. Please rephrase your question.",
                "query": user_query,
            }

        # Execute the SQL query
        mgr = get_sqlite_manager()
        try:
            with mgr.get_cursor() as cur:
                cur.execute(sql)

                # Check if this is a SELECT query
                if sql.strip().upper().startswith("SELECT"):
                    rows = cur.fetchall()
                    columns = (
                        [description[0] for description in cur.description]
                        if cur.description
                        else []
                    )
                    results = [dict(zip(columns, row)) for row in rows]

                    return {
                        "status": "success",
                        "query": user_query,
                        "sql": sql,
                        "results": results,
                        "count": len(results),
                    }
                else:
                    # For INSERT/UPDATE/DELETE
                    mgr.conn.commit()
                    return {
                        "status": "success",
                        "query": user_query,
                        "sql": sql,
                        "rows_affected": cur.rowcount,
                        "message": f"Query executed successfully. {cur.rowcount} row(s) affected.",
                    }
        except sqlite3.Error as e:
            logger.error(f"SQL execution error: {e}")
            return {
                "status": "error",
                "message": f"SQL execution failed: {str(e)}",
                "query": user_query,
                "sql": sql,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Natural language query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Qdrant Endpoints
# =============================================================================


@app.post("/api/memory/qdrant/chunk-and-ingest")
@limiter.limit("60/minute")
async def chunk_and_ingest(
    request: Request,
    directory: str = Query(""),
    files: List[UploadFile] = File(default=[]),
    api_key: str = Depends(verify_api_key),
):
    """Two-phase chunk + ingest with disk-backed safety."""
    import sys

    from app.documents.parser import SUPPORTED_EXTENSIONS

    content_type = request.headers.get("content-type", "")
    is_multipart = "multipart/form-data" in content_type

    if is_multipart:
        form_data = await request.form()
        effective_collection = (form_data.get("collection") or "").strip()
        chunk_size = int(form_data.get("chunk_size", 1000))
        chunk_overlap = int(form_data.get("chunk_overlap", 200))
    else:
        effective_collection = (request.query_params.get("collection") or "").strip()
        chunk_size = int(request.query_params.get("chunk_size", 1000))
        chunk_overlap = int(request.query_params.get("chunk_overlap", 200))

    print(
        f"!!! CHUNK_AND_INGEST: collection='{effective_collection}', dir='{directory}', files={len(files) if files else 0}",
        file=sys.stderr,
        flush=True,
    )

    if not effective_collection:
        raise HTTPException(status_code=400, detail="Collection name is required")

    qm = get_qdrant_manager()
    if not qm.qdrant_available:
        raise HTTPException(status_code=503, detail="Qdrant not available")

    if effective_collection not in qm.list_collections():
        qm.create_collection(effective_collection)

    try:
        qm.client.create_payload_index(
            collection_name=effective_collection,
            field_name="content_hash",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        print(
            f"    PAYLOAD INDEX: created for '{effective_collection}'",
            file=sys.stderr,
            flush=True,
        )
    except Exception as e:
        logger.debug(f"Payload index creation skipped: {e}")

    cache_dir = PROJECT_ROOT / "storage" / "chunk_cache" / effective_collection
    cache_dir.mkdir(parents=True, exist_ok=True)

    total_chunks_ref = [0]
    skipped_duplicates_ref = [0]
    files_processed_ref = [0]
    errors: list[str] = []

    source_files: list[tuple[str, Path]] = []

    if files and len(files) > 0:
        upload_tmp = cache_dir / "_uploads"
        upload_tmp.mkdir(parents=True, exist_ok=True)
        for file in files:
            try:
                safe_name = sanitize_filename(file.filename or "unnamed")
                dest = upload_tmp / safe_name
                content = await file.read()
                dest.write_bytes(content)
                source_files.append((safe_name, dest))
            except Exception as e:
                fname = file.filename or "unnamed"
                errors.append(f"{fname}: upload error: {str(e)}")

    elif directory:
        dir_path = Path(directory).expanduser().resolve()
        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(
                status_code=400, detail=f"Directory not found: {directory}"
            )

        all_files: list[Path] = []
        for ext in SUPPORTED_EXTENSIONS:
            all_files.extend(dir_path.rglob(f"*{ext}"))

        if not all_files:
            return {
                "status": "no_files",
                "message": f"No supported files found in {dir_path}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
            }

        for fp in all_files:
            source_files.append((str(fp.relative_to(dir_path)), fp))
    else:
        raise HTTPException(
            status_code=400, detail="Either files or directory must be provided"
        )

    if not source_files and not errors:
        return {"status": "no_files", "message": "All files were empty or unreadable"}

    print(f"    Processing {len(source_files)} files", file=sys.stderr, flush=True)

    phase1_results: list[tuple[str, int, bool]] = []

    for source_label, file_path in source_files:
        try:
            count, _, is_struct = await _phase1_chunk_file_to_disk(
                file_path, source_label, cache_dir, chunk_size, chunk_overlap
            )
            phase1_results.append((source_label, count, is_struct))
            print(
                f"    Phase1: {source_label} → {count} chunks, structured={is_struct}",
                file=sys.stderr,
                flush=True,
            )
        except Exception as e:
            import traceback

            print(f"    Phase1 ERROR: {source_label}: {e}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            errors.append(f"{source_label}: parsing/chunking failed: {str(e)}")

    upload_tmp = cache_dir / "_uploads"
    if upload_tmp.exists():
        try:
            shutil.rmtree(upload_tmp)
        except Exception:
            pass

    for source_label, expected_count, is_struct in phase1_results:
        if expected_count == 0:
            continue
        try:
            await _phase2_ingest_from_disk(
                cache_dir,
                source_label,
                qm,
                effective_collection,
                ws_manager,
                total_chunks_ref,
                skipped_duplicates_ref,
                files_processed_ref,
                is_struct,
            )
            files_processed_ref[0] += 1
        except Exception as e:
            logger.error(f"Phase 2 failed for '{source_label}': {e}", exc_info=True)
            errors.append(f"{source_label}: ingestion failed: {str(e)}")

    if not errors and cache_dir.exists():
        try:
            remaining = list(cache_dir.iterdir())
            if not remaining:
                cache_dir.rmdir()
        except Exception:
            pass

    print(
        f"    COMPLETE: {files_processed_ref[0]} files, {total_chunks_ref[0]} chunks, errors={len(errors)}",
        file=sys.stderr,
        flush=True,
    )

    total_ingested = total_chunks_ref[0]
    total_skipped = skipped_duplicates_ref[0]

    if total_ingested == 0 and total_skipped > 0:
        status_msg = "duplicate"
    elif total_ingested > 0 and total_skipped > 0:
        status_msg = "partial"
    elif total_ingested > 0:
        status_msg = "success"
    else:
        status_msg = "no_files"

    return {
        "status": status_msg,
        "files_processed": files_processed_ref[0],
        "total_chunks": total_ingested,
        "duplicates_skipped": total_skipped,
        "collection": effective_collection,
        "errors": errors if errors else None,
    }


@app.post("/api/memory/qdrant/search")
async def search_qdrant(request: SearchRequest):
    """Semantic search within a Qdrant collection."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        results = qm.search(request.collection, request.query, top_k=request.top_k)
        return {"results": results, "count": len(results)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed in '{request.collection}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/qdrant/collection")
async def manage_qdrant_collection(request: CollectionRequest):
    """Create or delete a Qdrant collection."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        if request.action == "create":
            qm.create_collection(request.name)
            return {"status": "created", "collection": request.name}
        if request.action == "delete":
            qm.delete_collection(request.name)
            return {"status": "deleted", "collection": request.name}
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to manage collection '{request.name}': {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/qdrant/collections")
async def get_qdrant_collections():
    """List all Qdrant collections."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            return {"collections": [], "available": False}

        collections = qm.list_collections()
        return {"collections": collections, "available": True}
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        return {"collections": [], "available": False, "error": str(e)}


@app.post("/api/memory/qdrant/delete")
async def delete_qdrant_documents(request: DeleteDocumentRequest):
    """Delete specific documents from a Qdrant collection by ID."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        deleted_count = qm.delete_documents(request.collection, request.document_ids)
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "collection": request.collection,
        }
    except Exception as e:
        logger.error(f"Failed to delete documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/qdrant/status")
async def get_qdrant_status():
    """Get Qdrant system status and actual storage size."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            return {"available": False, "collections_count": 0, "size": 0}

        collections = qm.list_collections()
        total_size = 0
        total_points = 0

        for col_name in collections:
            try:
                info = qm.client.get_collection(col_name)
                points = info.points_count or 0
                total_points += points

                vector_bytes = points * qm.vector_size * 4
                total_size += int(vector_bytes * 1.2)
            except Exception as e:
                logger.warning(f"Failed to get info for collection '{col_name}': {e}")

        return {
            "available": True,
            "collections_count": len(collections),
            "total_points": total_points,
            "size": total_size,
        }
    except Exception as e:
        logger.error(f"Failed to get Qdrant status: {e}")
        return {"available": False, "collections_count": 0, "size": 0, "error": str(e)}


@app.post("/api/memory/qdrant/generate-synthetic")
@limiter.limit("3/minute")
async def generate_synthetic_data(
    request: Request, synthetic_request: SyntheticDataRequest
):
    """Generate constraint-seeded synthetic data with compliance verification."""
    try:
        qm = get_qdrant_manager()
        if not qm.qdrant_available:
            raise HTTPException(status_code=503, detail="Qdrant not available")

        model = get_default_model()
        llm = _get_llm(model)

        purpose_prompts = {
            "adversarial": f"""Generate {synthetic_request.num_samples} adversarial prompts designed to test system prompt security.

Attack Vector: {synthetic_request.topic}

Each prompt should:
- Attempt to bypass system instructions
- Use techniques like prompt injection, jailbreaking, or role manipulation
- Be realistic and varied
- Include both subtle and obvious attacks

Format each prompt on a new line starting with "PROMPT:"

Begin:""",
            "error_recovery": f"""Generate {synthetic_request.num_samples} synthetic tool-use error scenarios and recovery steps.

Error Type: {synthetic_request.topic}

Format as:
REQUEST: [user request]
ERROR: [what went wrong]
RECOVERY: [how to fix it]
OUTCOME: [successful result]

Begin:""",
            "edge_cases": f"""Generate {synthetic_request.num_samples} edge case scenarios for testing.

Edge Case Type: {synthetic_request.topic}

Format as:
SCENARIO: [description]
PARAMETERS: [unusual inputs]
EXPECTED_BEHAVIOR: [correct response]

Begin:""",
            "constraint_validation": f"""Generate {synthetic_request.num_samples} test cases to validate system constraints.

Constraint to Test: {synthetic_request.topic}

Format as:
TEST_CASE: [scenario description]
INPUT: [user request]
EXPECTED_OUTPUT: [correct response showing constraint adherence]
CONSTRAINT_VERIFIED: [which constraint is being tested]

Begin:""",
        }

        prompt = purpose_prompts.get(
            synthetic_request.purpose, purpose_prompts["constraint_validation"]
        )
        logger.info(
            f"Generating {synthetic_request.num_samples} {synthetic_request.purpose} synthetic documents"
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(executor, lambda: llm.invoke(prompt))

        documents = parse_synthetic_response(response.content, synthetic_request)

        verified_docs = []
        for doc in documents:
            compliance_score = await verify_compliance(doc, synthetic_request)
            if compliance_score >= synthetic_request.compliance_threshold:
                doc.setdefault("metadata", {})["compliance_score"] = compliance_score
                verified_docs.append(doc)
            else:
                logger.warning(
                    f"Document failed compliance: {compliance_score}% < {synthetic_request.compliance_threshold}%"
                )

        if verified_docs:
            qm.ingest_documents(synthetic_request.collection, verified_docs)
            logger.info(
                f"Ingested {len(verified_docs)}/{len(documents)} verified documents"
            )

        return {
            "status": "success",
            "documents_generated": len(documents),
            "documents_verified": len(verified_docs),
            "compliance_rate": round((len(verified_docs) / len(documents)) * 100, 1)
            if documents
            else 0,
            "collection": synthetic_request.collection,
            "purpose": synthetic_request.purpose,
        }
    except Exception as e:
        logger.error(f"Failed to generate synthetic data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def verify_compliance(document: dict, request: SyntheticDataRequest) -> float:
    """Score generated document against compliance threshold."""
    content = document.get("content", "")

    checks = {
        "adversarial": lambda c: min(
            sum(
                10
                for kw in ["ignore", "forget", "bypass", "DAN", "jailbreak", "override"]
                if kw.lower() in c.lower()
            ),
            100,
        ),
        "error_recovery": lambda c: sum(
            25 for s in ["REQUEST:", "ERROR:", "RECOVERY:", "OUTCOME:"] if s in c
        ),
        "edge_cases": lambda c: min(
            sum(
                33 for s in ["SCENARIO:", "PARAMETERS:", "EXPECTED_BEHAVIOR:"] if s in c
            ),
            100,
        ),
        "constraint_validation": lambda c: sum(
            25
            for s in [
                "TEST_CASE:",
                "INPUT:",
                "EXPECTED_OUTPUT:",
                "CONSTRAINT_VERIFIED:",
            ]
            if s in c
        ),
    }

    scorer = checks.get(request.purpose)
    return scorer(content) if scorer else 50.0


def parse_synthetic_response(content: str, request: SyntheticDataRequest) -> list[dict]:
    """Parse LLM response into structured documents."""
    documents = []

    if request.purpose == "adversarial":
        prompts = [
            line.strip()
            for line in content.split("\n")
            if line.strip().startswith("PROMPT:")
        ]
        for i, prompt in enumerate(prompts):
            documents.append(
                {
                    "content": prompt.replace("PROMPT:", "").strip(),
                    "source": f"synthetic_{request.purpose}_{i + 1}",
                    "type": "synthetic",
                    "purpose": request.purpose,
                    "topic": request.topic,
                    "generated_at": datetime.now().isoformat(),
                }
            )
    else:
        sections = content.split("\n\n")
        for i, section in enumerate(sections):
            if section.strip() and len(section.strip()) > 50:
                documents.append(
                    {
                        "content": section.strip(),
                        "source": f"synthetic_{request.purpose}_{i + 1}",
                        "type": "synthetic",
                        "purpose": request.purpose,
                        "topic": request.topic,
                        "generated_at": datetime.now().isoformat(),
                    }
                )

    return documents


# =============================================================================
# Notes Endpoints
# =============================================================================


@app.get("/api/notes")
async def get_notes():
    """Get all notes from workspace."""
    try:
        notes_dir = WORKSPACE_PATH / "notes"
        if not notes_dir.exists():
            return {"notes": []}

        notes = []
        for note_file in sorted(notes_dir.glob("*.md")):
            content = note_file.read_text(encoding="utf-8")
            notes.append(
                {
                    "filename": note_file.name,
                    "content": content,
                    "size": len(content),
                    "modified": datetime.fromtimestamp(
                        note_file.stat().st_mtime
                    ).isoformat(),
                }
            )

        return {"notes": notes}
    except Exception as e:
        logger.error(f"Failed to get notes: {e}")
        return {"notes": []}


@app.post("/api/notes")
async def save_note(request: NoteSaveRequest):
    """Save a note to workspace."""
    try:
        notes_dir = WORKSPACE_PATH / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = "".join(
            c for c in request.filename if c.isalnum() or c in ".-_ "
        ).strip()
        if not safe_filename.endswith(".md"):
            safe_filename += ".md"

        note_path = notes_dir / safe_filename
        note_path.write_text(request.content, encoding="utf-8")

        return {
            "status": "saved",
            "filename": safe_filename,
            "path": str(note_path.relative_to(WORKSPACE_PATH)),
        }
    except Exception as e:
        logger.error(f"Failed to save note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/notes/{filename}")
async def delete_note(filename: str):
    """Delete a note from workspace."""
    try:
        note_path = WORKSPACE_PATH / "notes" / filename
        if note_path.exists():
            note_path.unlink()
            return {"status": "deleted"}
        raise HTTPException(status_code=404, detail="Note not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notes/save")
async def save_to_workspace(request: dict):
    """Save file content to workspace directory."""
    try:
        filename = request.get("filename")
        content = request.get("content")

        if not filename or content is None:
            raise HTTPException(
                status_code=400, detail="Filename and content are required"
            )

        safe_filename = "".join(
            c for c in filename if c.isalnum() or c in ".-_ "
        ).strip()
        if not safe_filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        file_path = WORKSPACE_PATH / safe_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return {
            "status": "success",
            "path": str(file_path.relative_to(WORKSPACE_PATH)),
            "filename": safe_filename,
        }
    except Exception as e:
        logger.error(f"Failed to save file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Voice Recognition Endpoint
# =============================================================================


@app.post("/api/voice/transcribe")
@limiter.limit("5/minute")
async def transcribe_audio(request: Request, file: UploadFile = File(...)):
    """Transcribe audio file to text using faster-whisper or Vosk."""
    import tempfile

    try:
        logger.info(f"Received audio file: {file.filename}, size: {file.size} bytes")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        logger.info(f"Saved temporary file: {tmp_path}")

        try:
            from app.voice.voice_recognition import transcribe_audio_file

            text = transcribe_audio_file(tmp_path)

            if not text:
                logger.warning("Transcription returned empty result")
                raise HTTPException(
                    status_code=400, detail="No speech detected or transcription failed"
                )

            logger.info(f"Transcription successful: {len(text)} characters")
            return {"text": text, "status": "success"}

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                logger.info(f"Cleaned up temporary file: {tmp_path}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# =============================================================================
# System Doctor Endpoint
# =============================================================================


@app.post("/api/system/doctor")
async def run_system_doctor():
    """Run comprehensive system diagnostics and auto-fix common issues."""
    import shutil
    import subprocess
    from datetime import datetime

    report = {
        "timestamp": datetime.now().isoformat(),
        "checks": [],
        "fixes_applied": [],
        "warnings": [],
        "errors": [],
    }

    try:
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/tags", method="GET"
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                model_count = len(data.get("models", []))
                report["checks"].append(
                    {
                        "name": "Ollama Connection",
                        "status": "pass",
                        "details": f"Connected with {model_count} models",
                    }
                )
        except Exception as e:
            report["checks"].append(
                {"name": "Ollama Connection", "status": "fail", "details": str(e)}
            )
            report["errors"].append("Ollama is not running. Start with: ollama serve")

        try:
            req = urllib.request.Request("http://127.0.0.1:6333/", method="GET")
            with urllib.request.urlopen(req, timeout=3):
                report["checks"].append(
                    {
                        "name": "Qdrant Connection",
                        "status": "pass",
                        "details": "Connected successfully",
                    }
                )
        except Exception as e:
            report["checks"].append(
                {"name": "Qdrant Connection", "status": "fail", "details": str(e)}
            )
            report["errors"].append("Qdrant is not running. Start with: ./qdrant")

        try:
            mgr = get_sqlite_manager()
            with mgr.get_cursor() as cur:
                cur.execute("PRAGMA integrity_check")
                result = cur.fetchone()[0]
                if result == "ok":
                    report["checks"].append(
                        {
                            "name": "SQLite Database",
                            "status": "pass",
                            "details": "Integrity check passed",
                        }
                    )
                else:
                    report["checks"].append(
                        {
                            "name": "SQLite Database",
                            "status": "fail",
                            "details": f"Integrity check failed: {result}",
                        }
                    )
                    report["errors"].append("Database integrity issue detected")
        except Exception as e:
            report["checks"].append(
                {"name": "SQLite Database", "status": "fail", "details": str(e)}
            )
            report["errors"].append(f"Database error: {str(e)}")

        try:
            if os.access(WORKSPACE_PATH, os.W_OK):
                report["checks"].append(
                    {
                        "name": "Workspace Permissions",
                        "status": "pass",
                        "details": "Writable",
                    }
                )
            else:
                report["checks"].append(
                    {
                        "name": "Workspace Permissions",
                        "status": "fail",
                        "details": "Not writable",
                    }
                )
                report["errors"].append("Workspace directory is not writable")
        except Exception as e:
            report["checks"].append(
                {"name": "Workspace Permissions", "status": "fail", "details": str(e)}
            )

        try:
            frontend_dist = PROJECT_ROOT / "frontend" / "dist" / "index.html"
            if frontend_dist.exists():
                report["checks"].append(
                    {
                        "name": "Frontend Build",
                        "status": "pass",
                        "details": "Build exists",
                    }
                )
            else:
                report["checks"].append(
                    {"name": "Frontend Build", "status": "fail", "details": "Missing"}
                )
                report["warnings"].append(
                    "Frontend not built. Run: cd frontend && npm run build"
                )
        except Exception as e:
            report["checks"].append(
                {"name": "Frontend Build", "status": "fail", "details": str(e)}
            )

        try:
            total, used, free = shutil.disk_usage(str(PROJECT_ROOT))
            free_gb = free // (1024**3)
            if free_gb > 5:
                report["checks"].append(
                    {
                        "name": "Disk Space",
                        "status": "pass",
                        "details": f"{free_gb} GB free",
                    }
                )
            else:
                report["checks"].append(
                    {
                        "name": "Disk Space",
                        "status": "warn",
                        "details": f"Only {free_gb} GB free",
                    }
                )
                report["warnings"].append(f"Low disk space: {free_gb} GB remaining")
        except Exception as e:
            report["checks"].append(
                {"name": "Disk Space", "status": "fail", "details": str(e)}
            )

        try:
            result = subprocess.run(
                [
                    "python3",
                    "-c",
                    "import fastapi, uvicorn, qdrant_client, sentence_transformers",
                ],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                report["checks"].append(
                    {
                        "name": "Python Dependencies",
                        "status": "pass",
                        "details": "All critical packages installed",
                    }
                )
            else:
                report["checks"].append(
                    {
                        "name": "Python Dependencies",
                        "status": "fail",
                        "details": "Missing packages",
                    }
                )
                report["errors"].append(
                    "Missing Python dependencies. Run: pip install -r requirements.txt"
                )
        except Exception as e:
            report["checks"].append(
                {"name": "Python Dependencies", "status": "fail", "details": str(e)}
            )

        pass_count = sum(1 for c in report["checks"] if c["status"] == "pass")
        total_count = len(report["checks"])
        report["summary"] = {
            "total_checks": total_count,
            "passed": pass_count,
            "failed": total_count - pass_count,
            "health_score": round((pass_count / total_count) * 100)
            if total_count > 0
            else 0,
        }

        report_file = (
            PROJECT_ROOT
            / f"doctor-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        report["report_file"] = str(report_file)

        return report

    except Exception as e:
        logger.error(f"System doctor failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket connection for live updates."""
    await ws_manager.connect(websocket)
    try:
        await ws_manager.send_personal(
            websocket,
            {
                "type": "connected",
                "message": "Connected to MAi-RAG-PA real-time updates",
                "heartbeat_status": heartbeat_state,
            },
        )

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    await ws_manager.send_personal(websocket, {"type": "pong"})
                elif msg_type == "subscribe":
                    channel = msg.get("channel", "")
                    await ws_manager.send_personal(
                        websocket,
                        {
                            "type": "subscribed",
                            "channel": channel,
                        },
                    )
                else:
                    await ws_manager.send_personal(
                        websocket,
                        {
                            "type": "error",
                            "message": f"Unknown message type: {msg_type}",
                        },
                    )
            except json.JSONDecodeError:
                await ws_manager.send_personal(
                    websocket,
                    {
                        "type": "error",
                        "message": "Invalid JSON",
                    },
                )

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await ws_manager.disconnect(websocket)


# =============================================================================
# Startup/Shutdown Events
# =============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global shutdown_flag
    shutdown_flag = False

    logger.info("MAi-RAG-PA API starting up...")

    try:
        mgr = get_sqlite_manager()
        existing_key = mgr.get("api_key")
        if not existing_key:
            from app.security.auth import generate_api_key

            new_key = generate_api_key()
            mgr.set("api_key", new_key)
            logger.info("API key auto-generated on first launch")
        else:
            logger.info("Existing API key found")
    except Exception as e:
        logger.warning(f"Auto-generate API key skipped: {e}")

    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))

        current_rev = command.current(alembic_cfg)
        head_rev = command.heads(alembic_cfg)

        if current_rev != head_rev:
            logger.info(
                f"Database schema outdated. Upgrading from {current_rev} to {head_rev}..."
            )
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migration completed successfully.")
        else:
            logger.info("Database schema is up to date.")
    except Exception as e:
        logger.warning(f"Auto-migration skipped (non-critical): {e}")
        logger.warning("App will continue with existing schema.")

    env_status = env_checker.check_all()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global shutdown_flag, heartbeat_task

    logger.info("MAi-RAG-PA API shutting down...")

    shutdown_flag = True

    if heartbeat_task and not heartbeat_task.done():
        logger.info("Cancelling heartbeat scheduler...")
        heartbeat_task.cancel()
        try:
            await asyncio.wait_for(heartbeat_task, timeout=5.0)
        except asyncio.CancelledError:
            logger.info("Heartbeat scheduler cancelled successfully")
        except asyncio.TimeoutError:
            logger.warning("Heartbeat scheduler didn't stop in time")
        except Exception as e:
            logger.warning(f"Error stopping heartbeat: {e}")

    try:
        if qdrant_manager and hasattr(qdrant_manager, "close"):
            qdrant_manager.close()
    except Exception as e:
        logger.warning(f"Qdrant close failed: {e}")

    try:
        if sqlite_manager and hasattr(sqlite_manager, "close"):
            sqlite_manager.close()
    except Exception as e:
        logger.warning(f"SQLite close failed: {e}")

    logger.info("MAi-RAG-PA API shutdown complete")


# =============================================================================
# Frontend Serving (MUST BE LAST)
# =============================================================================


@app.get("/")
async def serve_frontend():
    """Serve the frontend application."""
    frontend_path = PROJECT_ROOT / "frontend" / "dist" / "index.html"
    if frontend_path.exists():
        return FileResponse(str(frontend_path), headers={"Cache-Control": "no-cache"})
    return JSONResponse(
        status_code=404,
        content={
            "message": "MAi-RAG-PA API running. Frontend not built. Run: cd frontend && npm run build"
        },
    )


@app.get("/sounds/{filename}")
async def serve_sound(filename: str):
    """Serve sound files."""
    sound_path = PROJECT_ROOT / "frontend" / "public" / "sounds" / filename
    if sound_path.exists():
        return FileResponse(str(sound_path))
    raise HTTPException(status_code=404, detail="Sound file not found")


@app.get("/fonts/{path:path}")
async def serve_font(path: str):
    """Serve font files."""
    font_path = PROJECT_ROOT / "frontend" / "public" / "fonts" / path
    if font_path.exists():
        return FileResponse(str(font_path))
    raise HTTPException(status_code=404, detail="Font file not found")


@app.get("/{full_path:path}")
async def serve_static_files(full_path: str):
    """Serve static frontend files."""
    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    file_path = frontend_dist / full_path

    if file_path.is_dir() or not file_path.exists():
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), headers={"Cache-Control": "no-cache"})
        raise HTTPException(status_code=404, detail="Frontend not found")

    if full_path.startswith("assets/"):
        return FileResponse(
            str(file_path),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    return FileResponse(str(file_path))
