# app/memory/qdrant_manager.py
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (Distance, PointIdsList, PointStruct,
                                  VectorParams)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)


class QdrantMemoryManager:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.qdrant_url = f"http://{host}:{port}"
        self.qdrant_available = False
        self.client: Optional[QdrantClient] = None
        self.encoder: Optional[Any] = None
        self.vector_size = 384

        try:
            self.client = QdrantClient(url=self.qdrant_url, timeout=30)
            self.client.get_collections()
            self.qdrant_available = True
            logger.info("Qdrant connection successful")

            if SentenceTransformer is None:
                raise ImportError("sentence-transformers is not installed")

            local_model_path = (
                Path(__file__).parent.parent.parent / "models" / "all-MiniLM-L6-v2"
            )
            if local_model_path.exists():
                logger.info(
                    "Loading embedding model from local path: %s", local_model_path
                )
                try:
                    self.encoder = SentenceTransformer(str(local_model_path))
                except Exception:
                    self.encoder = SentenceTransformer(model_name)
            else:
                logger.warning(
                    "Local model not found at %s, using model name: %s",
                    local_model_path,
                    model_name,
                )
                self.encoder = SentenceTransformer(model_name)

            # Use new method name with fallback for older versions
            try:
                self.vector_size = int(self.encoder.get_embedding_dimension())
            except AttributeError:
                self.vector_size = int(self.encoder.get_sentence_embedding_dimension())

        except Exception as e:
            logger.warning("Qdrant initialization failed: %s", e)
            self.qdrant_available = False
            self.client = None
            self.encoder = None

    def list_collections(self) -> List[str]:
        """List all available subject collections."""
        if not self.qdrant_available or not self.client:
            return []
        return [c.name for c in self.client.get_collections().collections]

    def create_collection(self, collection_name: str) -> bool:
        """Create a new subject-centric collection."""
        if not self.qdrant_available or not self.client:
            return False
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )
            logger.info("✓ Created Qdrant collection: %s", collection_name)
            return True
        except Exception as e:
            logger.error(
                "Failed to create collection %s: %s", collection_name, e, exc_info=True
            )
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a Qdrant collection."""
        if not self.qdrant_available or not self.client:
            return False
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info("Deleted collection: %s", collection_name)
            return True
        except Exception as e:
            logger.error(
                "Failed to delete collection '%s': %s",
                collection_name,
                e,
                exc_info=True,
            )
            return False

    def ingest_documents(
        self, collection_name: str, documents: List[dict], batch_size: int = 32
    ) -> dict:
        """Embed and ingest pre-chunked documents into a collection."""
        if not self.qdrant_available or not self.client or not self.encoder:
            return {"status": "error", "message": "Qdrant not available"}

        if collection_name not in self.list_collections():
            return {
                "status": "error",
                "message": f"Collection '{collection_name}' does not exist",
            }

        points: List[PointStruct] = []
        for doc in documents:
            text = doc.get("content") or doc.get("text", "")
            if not text:
                continue

            vector = self.encoder.encode(text)
            vector = vector.tolist() if hasattr(vector, "tolist") else list(vector)
            point_id = str(uuid.uuid4())

            filename = doc.get("filename", doc.get("source", "unknown"))
            base_name = Path(filename).stem

            chapter = doc.get("chapter", "")
            page = doc.get("page", doc.get("page_number", ""))
            line_ref = doc.get("line_reference", doc.get("lines", ""))

            if not chapter and not page:
                ch_match = re.search(
                    r"(?:Chapter|Act|Scene)\s+(\d+|[IVXLCDM]+)", text, re.IGNORECASE
                )
                pg_match = re.search(r"(?:Page|p\.|pg\.)\s*(\d+)", text, re.IGNORECASE)
                if ch_match:
                    chapter = ch_match.group(0)
                if pg_match:
                    page = pg_match.group(1)

            payload = {
                "content": text,
                "source": filename,
                "filename": base_name,
                "collection": collection_name,
                "chapter": chapter,
                "page": page,
                "line_reference": line_ref,
                "doc_type": doc.get("type", "text"),
                "chunk_index": doc.get("chunk_index", 0),
                "total_chunks": doc.get("total_chunks", 1),
            }

            if doc.get("content_hash"):
                payload["content_hash"] = doc["content_hash"]
            if doc.get("payload"):
                payload["data"] = doc["payload"]

            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        try:
            for i in range(0, len(points), batch_size):
                self.client.upsert(
                    collection_name=collection_name,
                    points=points[i : i + batch_size],
                )
            return {
                "status": "success",
                "ingested": len(points),
                "collection": collection_name,
            }
        except Exception as e:
            logger.error("Qdrant upsert failed: %s", e, exc_info=True)
            return {"status": "error", "message": str(e)}

    def delete_documents(self, collection_name: str, document_ids: List[str]) -> int:
        """Delete specific documents by ID from a collection."""
        if not self.qdrant_available or not self.client:
            return 0

        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(points=document_ids),
            )
            return len(document_ids)
        except Exception as e:
            logger.error(
                "Failed to delete documents from %s: %s",
                collection_name,
                e,
                exc_info=True,
            )
            return 0

    def search(self, collection_name: str, query: str, top_k: int = 5) -> List[dict]:
        """Semantic search within a specific collection."""
        if not self.qdrant_available or not self.client or not self.encoder:
            return []

        try:
            query_embedding = self.encoder.encode(query)
            query_embedding = (
                query_embedding.tolist()
                if hasattr(query_embedding, "tolist")
                else list(query_embedding)
            )

            try:
                response = self.client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    limit=top_k,
                    with_payload=True,
                )
                results = response.points
            except AttributeError:
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    limit=top_k,
                    with_payload=True,
                )

            return [
                {
                    "text": r.payload.get("content", r.payload.get("text", "")),
                    "score": r.score,
                    "metadata": r.payload,
                }
                for r in results
            ]
        except Exception as e:
            logger.error("Search failed in '%s': %s", collection_name, e, exc_info=True)
            return []

    def _chunk_text(self, text: str, max_chunk_size: int = 512) -> List[str]:
        """Simple sentence-aware chunking."""
        sentences = re.split(r"[.!?]+\s*", text)
        chunks, current = [], []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(" ".join(current + [sent])) > max_chunk_size and current:
                chunks.append(" ".join(current))
                current = [sent]
            else:
                current.append(sent)
        if current:
            chunks.append(" ".join(current))
        return chunks

    def create_snapshot(self, collection_name: str) -> Optional[str]:
        """Create a snapshot of a Qdrant collection. Returns snapshot path or None."""
        if not self.qdrant_available or not self.client:
            logger.warning("Qdrant not available, cannot create snapshot")
            return None

        try:
            import concurrent.futures

            def _do_snapshot():
                return self.client.create_snapshot(collection_name=collection_name)

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_do_snapshot)
                snapshot_info = future.result(timeout=60)

            snapshot_path = (
                snapshot_info.location
                if hasattr(snapshot_info, "location")
                else str(snapshot_info)
            )
            logger.info("Created snapshot for '%s': %s", collection_name, snapshot_path)
            return snapshot_path
        except concurrent.futures.TimeoutError:
            logger.error(
                "Snapshot creation timed out after 60s for '%s'", collection_name
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to create snapshot for '%s': %s",
                collection_name,
                e,
                exc_info=True,
            )
            return None

    def list_snapshots(self, collection_name: str) -> List[dict]:
        """List all snapshots for a collection."""
        if not self.qdrant_available or not self.client:
            return []

        try:
            snapshots = self.client.list_snapshots(collection_name=collection_name)
            return [
                {
                    "name": s.name if hasattr(s, "name") else str(s),
                    "size": s.size if hasattr(s, "size") else 0,
                    "created_at": str(s.creation_time)
                    if hasattr(s, "creation_time")
                    else "unknown",
                }
                for s in snapshots
            ]
        except Exception as e:
            logger.error(
                "Failed to list snapshots for '%s': %s",
                collection_name,
                e,
                exc_info=True,
            )
            return []

    def delete_snapshot(self, collection_name: str, snapshot_name: str) -> bool:
        """Delete a specific snapshot."""
        if not self.qdrant_available or not self.client:
            return False

        try:
            self.client.delete_snapshot(
                collection_name=collection_name,
                snapshot_name=snapshot_name,
            )
            logger.info(
                "Deleted snapshot '%s' from '%s'", snapshot_name, collection_name
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to delete snapshot '%s': %s", snapshot_name, e, exc_info=True
            )
            return False

    def rotate_snapshots(self, collection_name: str, keep: int = 7) -> int:
        """Keep only the last N snapshots per collection. Returns count deleted."""
        snapshots = self.list_snapshots(collection_name)
        if len(snapshots) <= keep:
            return 0

        sorted_snaps = sorted(
            snapshots, key=lambda s: s.get("created_at", ""), reverse=True
        )
        to_delete = sorted_snaps[keep:]
        deleted = 0

        for snap in to_delete:
            if self.delete_snapshot(collection_name, snap["name"]):
                deleted += 1

        logger.info(
            "Rotated snapshots for '%s': kept %s, deleted %s",
            collection_name,
            keep,
            deleted,
        )
        return deleted

    def backup_all_collections(
        self, backup_dir: Optional[Path] = None, keep: int = 7
    ) -> dict:
        """Create snapshots for all collections and rotate old ones."""
        if backup_dir is None:
            backup_dir = Path(__file__).parent.parent.resolve() / "backups" / "qdrant"
        backup_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        collections = self.list_collections()

        for collection in collections:
            snapshot_path = self.create_snapshot(collection)
            if snapshot_path:
                self.rotate_snapshots(collection, keep=keep)
                results[collection] = {
                    "snapshot": snapshot_path,
                    "status": "success",
                }
            else:
                results[collection] = {
                    "snapshot": None,
                    "status": "failed",
                }

        logger.info("Qdrant backup complete: %s collections processed", len(results))
        return results
