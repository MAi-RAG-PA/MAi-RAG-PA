# app/rag/rag_core.py
from __future__ import annotations

import json
import logging
import urllib.request
import uuid
from pathlib import Path
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import Config
from app.documents.chunker import chunk_text_semantic
from app.documents.processor import process_directory

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent


class RAGCore:
    def __init__(self, collection_name: str = "local_docs"):
        """Initialize RAG Core with Ollama embeddings and Qdrant client."""
        self.collection_name = collection_name
        self.vector_size = Config.EMBEDDING_DIM
        self.ollama_url = Config.OLLAMA_URL
        self.embedding_model = Config.EMBEDDING_MODEL

        logger.info(
            "RAGCore using Ollama embeddings: model=%s, dim=%s",
            self.embedding_model,
            self.vector_size,
        )

        self.client = QdrantClient(host="localhost", port=6333)
        self._ensure_collection()

    def _embed(self, text: str) -> Optional[List[float]]:
        """Get embedding vector from Ollama."""
        try:
            payload = json.dumps(
                {
                    "model": self.embedding_model,
                    "prompt": text,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                f"{self.ollama_url}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("embedding")
        except Exception as e:
            logger.error("Ollama embedding failed: %s", e)
            return None

    def _ensure_collection(self):
        """Create the default collection if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(
                "Created collection '%s' (dim=%s)",
                self.collection_name,
                self.vector_size,
            )

    def add_document(
        self, text: str, doc_id: Optional[str] = None, chunk_max_words: int = 300
    ) -> int:
        """Add a single document to the knowledge base using semantic chunking."""
        chunks = chunk_text_semantic(
            text, max_words=chunk_max_words, overlap_sentences=2
        )
        if not chunks:
            return 0

        points = []
        for idx, chunk in enumerate(chunks, 1):
            vector = self._embed(chunk)
            if vector is None:
                continue
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "text": chunk,
                        "source": doc_id or "unknown",
                        "chunk_index": idx,
                    },
                )
            )

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    def add_directory(self, directory_path: Optional[str] = None) -> int:
        """Add all supported files in a directory to the knowledge base."""
        if directory_path is None:
            dir_path = PROJECT_ROOT / "documents_storage"
        else:
            dir_path = Path(directory_path).expanduser()

        if not dir_path.exists():
            logger.error("Directory not found: %s", dir_path)
            return 0

        chunks_data = process_directory(dir_path)
        if not chunks_data:
            logger.info("No chunks extracted from %s", dir_path)
            return 0

        points = []
        for data in chunks_data:
            vector = self._embed(data["text"])
            if vector is None:
                continue
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={**data["metadata"], "text": data["text"]},
                )
            )

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
            logger.info("Upserted %s chunks from %s", len(points), dir_path)
        return len(points)

    def query(self, question: str, limit: int = 3) -> List[str]:
        """Query the knowledge base."""
        vector = self._embed(question)
        if vector is None:
            return []

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit,
        )
        return [r.payload.get("text", "") for r in results]
