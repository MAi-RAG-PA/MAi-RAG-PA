import os

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Qdrant server config
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# Model storage path
MODELS_DIR = os.path.join(PROJECT_ROOT, "models_storage")

# Document storage path
DOCUMENTS_DIR = os.path.join(PROJECT_ROOT, "documents_storage")

# Embedding model config
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# LLM model config (placeholder)
LLM_MODEL_NAME = "your-llm-model-name"

# Other configs
CHUNK_SIZE = 500  # tokens or characters per chunk
