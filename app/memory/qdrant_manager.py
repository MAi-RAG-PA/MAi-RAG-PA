# ~/MAi-RAG/app/memory/qdrant_manager.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, PointIdsList
from sentence_transformers import SentenceTransformer
from pathlib import Path
import uuid
import logging
import re

logger = logging.getLogger(__name__)


class QdrantMemoryManager:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.qdrant_available = False
        self.client = None
        self.encoder = None
        self.vector_size = 384  # Default for all-MiniLM-L6-v2
        
        try:
            self.client = QdrantClient(host=host, port=port)
            # Test connection
            self.client.get_collections()
            self.qdrant_available = True
            logger.info("✅ Qdrant connection successful")
            
            # Initialize encoder with local model path
            local_model_path = Path(__file__).parent.parent.parent / "models" / "all-MiniLM-L6-v2"
            if local_model_path.exists():
                logger.info(f"Loading embedding model from local path: {local_model_path}")
                self.encoder = SentenceTransformer(str(local_model_path), local_files_only=True)
            else:
                logger.warning(f"Local model not found at {local_model_path}, using model name: {model_name}")
                self.encoder = SentenceTransformer(model_name, local_files_only=True)
            
            self.vector_size = self.encoder.get_sentence_embedding_dimension()
            
        except Exception as e:
            logger.warning(f"⚠️ Qdrant initialization failed: {e}")
            self.qdrant_available = False

    def list_collections(self) -> list[str]:
        """List all available subject collections"""
        if not self.qdrant_available:
            return []
        return [c.name for c in self.client.get_collections().collections]

    def create_collection(self, collection_name: str) -> bool:
        """Create a new subject-centric collection"""
        if not self.qdrant_available:
            return False
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
                hnsw_config={"m": 16, "ef_construct": 100},
            )
            logger.info(f"✓ Created Qdrant collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create collection {collection_name}: {e}")
            return False

    def ingest_documents(
        self, collection_name: str, documents: list[dict], batch_size: int = 32
    ) -> dict:
        """Chunk, embed, and ingest documents into a collection."""
        if not self.qdrant_available:
            return {"status": "error", "message": "Qdrant not available"}
            
        if collection_name not in self.list_collections():
            return {
                "status": "error",
                "message": f"Collection '{collection_name}' does not exist",
            }

        points = []
        for doc in documents:
            # Handle both 'text' and 'content' keys
            text = doc.get("text") or doc.get("content", "")
            if not text:
                continue
                
            chunks = self._chunk_text(text, max_chunk_size=512)
            for i, chunk in enumerate(chunks):
                vector = self.encoder.encode(chunk).tolist()
                point_id = str(uuid.uuid4())
                
                # Build metadata safely
                metadata = doc.get("metadata", {})
                if not metadata:
                    metadata = {"source": doc.get("source", "unknown")}
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "text": chunk,
                            "source": metadata.get("source", "unknown"),
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            **metadata,
                        },
                    )
                )

        try:
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                self.client.upsert(collection_name=collection_name, points=batch)

            return {
                "status": "success",
                "ingested": len(points),
                "collection": collection_name,
            }
        except Exception as e:
            logger.error(f"❌ Qdrant upsert failed: {e}")
            return {"status": "error", "message": str(e)}

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> int:
        """Delete specific documents by ID from a collection."""
        if not self.qdrant_available:
            return 0
    
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(
                    points=document_ids
                )
            )
            return len(document_ids)
        except Exception as e:
            logger.error(f"Failed to delete documents from {collection_name}: {e}")
            return 0

    def search(self, collection_name: str, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search within a specific collection"""
        if not self.qdrant_available:
            return []
            
        query_vector = self.encoder.encode(query).tolist()
        results = self.client.search(
            collection_name=collection_name, query_vector=query_vector, limit=top_k
        )
        return [
            {
                "text": r.payload["text"],
                "score": r.score,
                "metadata": r.payload,
            }
            for r in results
        ]

    def _chunk_text(self, text: str, max_chunk_size: int = 512) -> list[str]:
        """Simple sentence-aware chunking"""
        sentences = re.split(r"[.!?]+\s*", text)
        chunks, current = [], []
        for sent in sentences:
            if len(" ".join(current + [sent])) > max_chunk_size and current:
                chunks.append(" ".join(current))
                current = [sent]
            else:
                current.append(sent)
        if current:
            chunks.append(" ".join(current))
        return chunks
