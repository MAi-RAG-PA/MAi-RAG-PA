# ~/MAi-RAG/app/rag/generator.py
import os
import threading
from app.rag.ollama_client import OllamaClient

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11435")

class OllamaModel:
    def __init__(self):
        self.ollama = OllamaClient(model_name="llama3-chatqa:8b")

    def generate(self, prompt: str) -> str:
        return self.ollama.generate(prompt)

MODEL_REGISTRY = {
    "ollama": OllamaModel(),
}

_model_lock = threading.Lock()

def generate_answer(prompt: str, model_name: str = "ollama") -> str:
    with _model_lock:
        model = MODEL_REGISTRY.get(model_name)
        if not model:
            return f"Error: Model '{model_name}' not found."
        return model.generate(prompt)
