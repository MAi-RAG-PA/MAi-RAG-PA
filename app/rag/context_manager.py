# app/rag/context_manager.py
"""
Context window management for MAi-RAG.
Fully model-agnostic - queries Ollama for actual model capabilities.
Prevents token overflow by truncating history and documents to fit model limits.
"""
import json
import logging
import re
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_LIMIT = 8_192
RESERVE_TOKENS = 2_048
CHARS_PER_TOKEN = 4

_model_info_cache: dict[str, dict] = {}


def _fetch_model_info(
    model_name: str, ollama_url: str = "http://127.0.0.1:11434"
) -> dict:
    """Fetch model metadata from Ollama /api/show endpoint."""
    if model_name in _model_info_cache:
        return _model_info_cache[model_name]

    try:
        payload = json.dumps({"model": model_name}).encode("utf-8")
        req = urllib.request.Request(
            f"{ollama_url}/api/show",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            _model_info_cache[model_name] = data
            return data
    except Exception as e:
        logger.debug("Could not fetch model info for '%s': %s", model_name, e)
        return {}


def get_context_limit(
    model_name: str, ollama_url: str = "http://127.0.0.1:11434"
) -> int:
    """Get the context window limit for a model by querying Ollama."""
    info = _fetch_model_info(model_name, ollama_url)

    lower_name = model_name.lower()

    ctx_match = re.search(r"(\d+)[mM](?:tp)?", lower_name)
    if ctx_match:
        ctx = int(ctx_match.group(1)) * 1_000_000
        logger.debug("Model '%s' context from name pattern: %s", model_name, ctx)
        return ctx

    k_match = re.search(r"(\d+)[kK]", lower_name)
    if k_match:
        ctx = int(k_match.group(1)) * 1_000
        logger.debug("Model '%s' context from name pattern: %s", model_name, ctx)
        return ctx

    params = info.get("parameters", "")
    if isinstance(params, str):
        for line in params.split("\n"):
            if "num_ctx" in line.lower():
                try:
                    ctx = int(line.strip().split()[-1])
                    if ctx > 0:
                        logger.debug(
                            "Model '%s' context from num_ctx: %s", model_name, ctx
                        )
                        return ctx
                except (ValueError, IndexError):
                    pass

    details = info.get("model_info", {})
    if isinstance(details, dict):
        for key in ["context_length", "max_context_length", "rope.freq_base"]:
            if key in details:
                try:
                    ctx = int(details[key])
                    if ctx > 0:
                        logger.debug(
                            "Model '%s' context from %s: %s", model_name, key, ctx
                        )
                        return ctx
                except (ValueError, TypeError):
                    pass

    family = info.get("details", {}).get("family", "").lower()
    family_limits = {
        "llama": 131_072,
        "qwen2": 131_072,
        "qwen3": 131_072,
        "mistral": 32_768,
        "gemma": 8_192,
        "phi": 131_072,
        "command-r": 128_000,
        "deepseek": 131_072,
        "codellama": 16_384,
    }
    for fam, limit in family_limits.items():
        if fam in family:
            logger.debug(
                "Model '%s' context from family '%s': %s", model_name, fam, limit
            )
            return limit

    logger.warning(
        "Could not determine context limit for '%s', using default %s",
        model_name,
        DEFAULT_CONTEXT_LIMIT,
    )
    return DEFAULT_CONTEXT_LIMIT


def estimate_tokens(text: str) -> int:
    """Estimate token count from character length."""
    if not text:
        return 0
    return len(text) // CHARS_PER_TOKEN


def truncate_text(text: str, max_tokens: int) -> str:
    """Truncate text to fit within token limit."""
    if not text:
        return text

    estimated = estimate_tokens(text)
    if estimated <= max_tokens:
        return text

    max_chars = max_tokens * CHARS_PER_TOKEN
    truncated = text[:max_chars]

    last_newline = truncated.rfind("\n")
    if last_newline > max_chars * 0.8:
        truncated = truncated[:last_newline]

    logger.info(
        "Truncated text from %s to ~%s tokens (%s → %s chars)",
        estimated,
        max_tokens,
        len(text),
        len(truncated),
    )
    return truncated + "\n\n[... content truncated to fit context window ...]"


def build_context_window(
    system_prompt: str,
    chat_history: list[dict],
    user_message: str,
    retrieved_docs: Optional[list[str]] = None,
    model_name: str = "default",
    ollama_url: str = "http://127.0.0.1:11434",
) -> str:
    """Build a prompt that fits within the model's context window."""
    context_limit = get_context_limit(model_name, ollama_url)
    available_tokens = context_limit - RESERVE_TOKENS

    system_tokens = estimate_tokens(system_prompt)
    available_tokens -= system_tokens

    user_tokens = estimate_tokens(user_message)
    available_tokens -= user_tokens

    if available_tokens < 0:
        logger.error(
            "System prompt + user message exceed context limit for %s", model_name
        )
        available_tokens = 0

    docs_text = ""
    if retrieved_docs:
        docs_combined = "\n\n---\n\n".join(retrieved_docs)
        docs_tokens = estimate_tokens(docs_combined)

        if docs_tokens <= available_tokens:
            docs_text = docs_combined
            available_tokens -= docs_tokens
        else:
            docs_text = truncate_text(docs_combined, available_tokens)
            available_tokens -= estimate_tokens(docs_text)
            logger.info("RAG documents truncated to fit context window")

    history_parts = []
    dropped_count = 0
    for msg in reversed(chat_history):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        entry = f"{role.capitalize()}: {content}"
        entry_tokens = estimate_tokens(entry)

        if entry_tokens <= available_tokens:
            history_parts.insert(0, entry)
            available_tokens -= entry_tokens
        else:
            dropped_count += 1

    if dropped_count:
        logger.info("Dropped %s older messages to fit context", dropped_count)

    parts = [system_prompt]
    if history_parts:
        parts.append("\n\nChat History:\n" + "\n".join(history_parts))
    if docs_text:
        parts.append("\n\nRelevant Context:\n" + docs_text)
    parts.append(f"\n\nUser: {user_message}\nAssistant:")

    final_prompt = "\n".join(parts)
    final_tokens = estimate_tokens(final_prompt)

    logger.info(
        "Context built for %s: %s/%s tokens (history=%s msgs, docs=%s)",
        model_name,
        final_tokens,
        context_limit,
        len(history_parts),
        len(retrieved_docs or []),
    )

    return final_prompt


def clear_model_cache():
    """Clear the model info cache (call when models change)."""
    _model_info_cache.clear()
