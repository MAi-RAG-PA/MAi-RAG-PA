# app/rag/model_manager.py
"""
Model management with automatic fallback for MAi-RAG.
Fully model-agnostic - works with any Ollama model family.
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_TTL = 60


class ModelManager:
    """Manages Ollama model availability and provides fallback selection."""

    def __init__(self, ollama_url: str = "http://127.0.0.1:11434"):
        self.ollama_url = ollama_url
        self._available_models: list[str] = []
        self._last_check: float = 0

    def get_available_models(self, force_refresh: bool = False) -> list[str]:
        """Fetch available models from Ollama with caching."""
        now = time.time()

        if (
            not force_refresh
            and self._available_models
            and (now - self._last_check) < _CACHE_TTL
        ):
            return self._available_models

        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = data.get("models", [])
                self._available_models = [
                    m["name"] for m in models if isinstance(m, dict) and m.get("name")
                ]
                self._last_check = now
                logger.info(
                    "Ollama models refreshed: %s available", len(self._available_models)
                )
        except Exception as e:
            logger.warning("Failed to fetch Ollama models: %s", e)
            if not self._available_models:
                self._available_models = []

        return self._available_models

    def _build_fallback_chain(self) -> list[str]:
        """Dynamically build fallback chain from available models."""
        available = self.get_available_models()
        if not available:
            return []

        embedding_patterns = [
            "embed",
            "nomic-embed",
            "mxbai-embed",
            "all-minilm",
            "bge-",
            "e5-",
        ]
        chat_models = [
            m for m in available if not any(p in m.lower() for p in embedding_patterns)
        ]

        if not chat_models:
            return available

        def sort_key(model_name: str) -> tuple:
            lower = model_name.lower()

            is_chatty = (
                1 if any(k in lower for k in ["coder", "instruct", "chat", "it"]) else 0
            )

            size = 0.0
            for token in re.split(r"[-_ ]+", lower):
                if token.endswith("b"):
                    try:
                        size = float(token[:-1])
                        break
                    except ValueError:
                        pass
                elif token.endswith("m") and "b" not in token:
                    try:
                        size = float(token[:-1]) / 1000.0
                        break
                    except ValueError:
                        pass

            return (-is_chatty, -size, model_name)

        return sorted(chat_models, key=sort_key)

    def resolve_model(self, requested: Optional[str] = None) -> str:
        """Resolve a model name with automatic fallback."""
        available = self.get_available_models()

        if not available:
            raise RuntimeError("No Ollama models available. Is Ollama running?")

        if requested and requested in available:
            return requested

        if requested:
            partial_matches = [m for m in available if requested.lower() in m.lower()]
            if partial_matches:
                resolved = partial_matches[0]
                logger.info(
                    "Model '%s' resolved to '%s' via partial match", requested, resolved
                )
                return resolved
            logger.warning(
                "Requested model '%s' not available, falling back", requested
            )

        chain = self._build_fallback_chain()
        if chain:
            fallback = chain[0]
            if requested:
                logger.warning("Fallback: '%s' → '%s'", requested, fallback)
            return fallback

        fallback = available[0]
        logger.warning("No suitable fallback found, using '%s'", fallback)
        return fallback

    def is_available(self, model_name: str) -> bool:
        """Check if a specific model is currently available."""
        return model_name in self.get_available_models()

    def get_chat_models(self) -> list[str]:
        """Get available chat models (excluding embedding models)."""
        embedding_patterns = [
            "embed",
            "nomic-embed",
            "mxbai-embed",
            "all-minilm",
            "bge-",
            "e5-",
        ]
        available = self.get_available_models()
        return [
            m for m in available if not any(p in m.lower() for p in embedding_patterns)
        ]

    def get_fallback_chain(self) -> list[str]:
        """Get the current dynamic fallback chain."""
        return self._build_fallback_chain()
