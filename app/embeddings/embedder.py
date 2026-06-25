# ~MAi-RAG/app/embeddings/embedder.py
from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL_NAME

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    def embed(self, texts: list) -> list:
        """
        Generate embeddings for a list of texts.
        """
        return self.model.encode(texts, convert_to_numpy=True).tolist()
