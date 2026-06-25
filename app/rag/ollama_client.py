# ~/MAi-RAG/app/rag/ollama_client.py

import os
import requests

class OllamaClient:
    def __init__(self, model_name="llama3-chatqa:8b"):
        self.model_name = model_name
        self.base_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11435")

    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        url = f"{self.base_url}/v1/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": max_tokens,
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("text", "")
        except requests.RequestException as e:
            # Log or handle error as needed
            print(f"Error calling Ollama API: {e}")
            return "Error: Failed to generate response from Ollama."
