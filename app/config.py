# app/config.py
import os


class Config:
    # LLM & RAG Settings
    CONTEXT_WINDOW = int(os.getenv("MAI_CONTEXT_WINDOW", "8192"))
    RAG_TOP_K = int(os.getenv("MAI_RAG_TOP_K", "5"))

    # Embedding Settings (Ollama)
    EMBEDDING_MODEL = os.getenv("MAI_EMBEDDING_MODEL", "nomic-embed-text:latest")
    EMBEDDING_DIM = int(os.getenv("MAI_EMBEDDING_DIM", "768"))
    OLLAMA_URL = os.getenv("MAI_OLLAMA_URL", "http://127.0.0.1:11434")

    # Ingestion Settings
    BATCH_SIZE = int(os.getenv("MAI_BATCH_SIZE", "64"))

    # Rate Limiting
    RATE_LIMIT_CHAT = os.getenv("MAI_RATE_LIMIT_CHAT", "30/minute")
    RATE_LIMIT_INGEST = os.getenv("MAI_RATE_LIMIT_INGEST", "5/minute")
