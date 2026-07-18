# app/rag/rag_core.py
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from app.documents.chunker import chunk_text_semantic
from app.documents.processor import process_directory

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent


class RAGCore:
    def __init__(self, collection_name: str = "local_docs"):
        """Initialize RAG Core with embedding model and Qdrant client."""
        self.collection_name = collection_name

        model_path = PROJECT_ROOT / "models" / "all-MiniLM-L6-v2"
        logger.info("Loading embedding model from %s", model_path)
        self.encoder = SentenceTransformer(str(model_path))

        self.client = QdrantClient(host="localhost", port=6333)
        self._ensure_collection()

    def _get_vector_size(self) -> int:
        try:
            return int(self.encoder.get_embedding_dimension())
        except AttributeError:
            return int(self.encoder.get_sentence_embedding_dimension())

    def _ensure_collection(self):
        """Create the default collection if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            vector_size = self._get_vector_size()
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Created agnostic collection '%s'", self.collection_name)

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
            vector = self.encoder.encode(chunk)
            vector = vector.tolist() if hasattr(vector, "tolist") else list(vector)
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

        self.client.upsert(collection_name=self.collection_name, points=points)
        return len(chunks)

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
            vector = self.encoder.encode(data["text"])
            vector = vector.tolist() if hasattr(vector, "tolist") else list(vector)
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={**data["metadata"], "text": data["text"]},
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info("Upserted %s chunks from %s", len(points), dir_path)
        return len(points)

    def query(self, question: str, limit: int = 3) -> List[str]:
        """Query the knowledge base."""
        vector = self.encoder.encode(question)
        vector = vector.tolist() if hasattr(vector, "tolist") else list(vector)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit,
        )
        return [r.payload.get("text", "") for r in results]
