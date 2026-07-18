# app/rag/rag_server.py
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.rag.rag_core import RAGCore

logger = logging.getLogger(__name__)
router = APIRouter()

_rag_core = None


def get_rag_core() -> RAGCore:
    """Lazy initialization of RAG Core."""
    global _rag_core
    if _rag_core is None:
        try:
            _rag_core = RAGCore(collection_name="local_docs")
            logger.info("RAG Core initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize RAG Core: %s", e, exc_info=True)
            raise HTTPException(
                status_code=503, detail=f"RAG system not available: {str(e)}"
            )
    return _rag_core


class DocumentRequest(BaseModel):
    text: str
    doc_id: Optional[str] = None
    chunk_max_words: int = 300


class QueryRequest(BaseModel):
    query: str
    limit: int = 3


class DirectoryRequest(BaseModel):
    directory: Optional[str] = None


@router.post("/add")
async def add_document(req: DocumentRequest):
    """Add text document to knowledge base"""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided")

    try:
        rag_core = get_rag_core()
        chunks = rag_core.add_document(
            req.text,
            doc_id=req.doc_id,
            chunk_max_words=req.chunk_max_words,
        )
        return {"status": "success", "chunks": chunks}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add document: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query(req: QueryRequest):
    """Query the knowledge base"""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="No query provided")

    try:
        rag_core = get_rag_core()
        results = rag_core.query(req.query, limit=req.limit)
        return {"status": "success", "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Query failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_directory")
async def add_directory(req: DirectoryRequest):
    """Add all supported files from a directory"""
    try:
        dir_path = req.directory
        if dir_path is None:
            dir_path = Path.home() / "MAi-RAG" / "documents_storage"
        else:
            dir_path = Path(dir_path).expanduser()

        rag_core = get_rag_core()
        total_chunks = rag_core.add_directory(str(dir_path))
        return {"status": "success", "total_chunks": total_chunks}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Directory ingestion failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
