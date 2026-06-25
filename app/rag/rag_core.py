# ~/MAi-RAG/app/rag/rag_core.py
import uuid
import logging
from pathlib import Path
from typing import List, Optional

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.documents.chunker import chunk_text_semantic
from app.documents.processor import process_directory

logger = logging.getLogger(__name__)

# Cross-platform project root definition
PROJECT_ROOT = Path(__file__).parent.parent.parent

class RAGCore:
    def __init__(self, collection_name: str = "local_docs"):
        """Initialize RAG Core with embedding model and Qdrant client."""
        self.collection_name = collection_name
        
        # Load the bundled embedding model
        model_path = PROJECT_ROOT / "models" / "all-MiniLM-L6-v2"
        logger.info(f"Loading embedding model from {model_path}")
        self.encoder = SentenceTransformer(str(model_path))
        
        # Connect to Qdrant
        self.client = QdrantClient(host="localhost", port=6333)
        
        # Ensure the default collection exists
        self._ensure_collection()

    def _ensure_collection(self):
        """Create the default collection if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.encoder.get_sentence_embedding_dimension(), 
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"Created agnostic collection '{self.collection_name}'")

    def add_document(self, text: str, doc_id: Optional[str] = None, chunk_max_words: int = 300) -> int:
        """Add a single document to the knowledge base using semantic chunking."""
        # Use the new semantic chunker instead of naive character splitting
        chunks = chunk_text_semantic(text, max_words=chunk_max_words, overlap_sentences=2)
        
        if not chunks:
            return 0

        points = []
        for idx, chunk in enumerate(chunks, 1):
            vector = self.encoder.encode(chunk).tolist()
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "text": chunk,
                        "source": doc_id or "unknown",
                        "chunk_index": idx
                    }
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
            logger.error(f"Directory not found: {dir_path}")
            return 0

        # Use the new processor which handles PDF, EPUB, TXT and semantic chunking
        chunks_data = process_directory(dir_path)
        
        if not chunks_data:
            logger.info(f"No chunks extracted from {dir_path}")
            return 0

        points = []
        for data in chunks_data:
            vector = self.encoder.encode(data["text"]).tolist()
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={**data["metadata"], "text": data["text"]}
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"Upserted {len(points)} chunks from {dir_path}")
        return len(points)

    def query(self, question: str, limit: int = 3) -> List[str]:
        """Query the knowledge base."""
        vector = self.encoder.encode(question).tolist()
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit
        )
        return [r.payload.get("text", "") for r in results]
