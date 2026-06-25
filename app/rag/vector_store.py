# ~/MAi-RAG/app/rag/vector_store.py
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import logging
import hashlib
import uuid

logger = logging.getLogger(__name__)

# Cross-platform path to bundled model
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "all-MiniLM-L6-v2"

class VectorStore:
    def __init__(self, collection_name: str = "local_docs"):
        self.collection_name = collection_name
        self.client = QdrantClient(host="localhost", port=6333)
        
        # Load the bundled embedding model with local_files_only=True
        logger.info(f"Loading embedding model from {MODEL_PATH}")
        self.embedding_model = SentenceTransformer(str(MODEL_PATH), local_files_only=True)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
    def init_collection(self):
        """Create collection if it doesn't exist"""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE)
            )
            logger.info(f"Created collection '{self.collection_name}' with dimension {self.embedding_dim}")
    
    def generate_point_id(self, metadata: dict) -> str:
        """Generate stable UUID based on metadata"""
        unique_str = f"{metadata.get('source_file', '')}_{metadata.get('chunk_index', '')}"
        sha256_hash = hashlib.sha256(unique_str.encode('utf-8')).digest()
        point_uuid = uuid.UUID(bytes=sha256_hash[:16])
        return str(point_uuid)
    
    def ingest_chunks(self, chunks: list, batch_size: int = 256):
        """Embed and upsert chunks into Qdrant"""
        self.init_collection()
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts = [c['text'] for c in batch]
            metadatas = [c['metadata'] for c in batch]
            
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            points = []
            for idx, emb in enumerate(embeddings):
                metadata = metadatas[idx]
                point_id = self.generate_point_id(metadata)
                payload = {
                    "text": texts[idx],
                    **metadata
                }
                points.append(PointStruct(
                    id=point_id,
                    vector=emb.tolist(),
                    payload=payload
                ))
            
            self.client.upsert(collection_name=self.collection_name, points=points)
            logger.info(f"Upserted batch {i//batch_size + 1} with {len(points)} vectors")
        
        return len(chunks)
    
    def search(self, query: str, top_k: int = 5) -> list:
        """Search the knowledge base"""
        query_embedding = self.embedding_model.encode(query).tolist()
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        
        return [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload
            }
            for r in results
        ]

# Singleton instance
_vector_store = None

def get_vector_store(collection_name: str = "local_docs") -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(collection_name)
    return _vector_store
