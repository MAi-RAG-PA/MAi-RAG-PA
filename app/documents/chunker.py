# /app/documents/chunker.py
import logging
import re
from typing import List, Optional

import spacy

logger = logging.getLogger(__name__)

_nlp = None


def get_nlp():
    """Lazy load SpaCy model to avoid startup overhead."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
            _nlp.max_length = 18_000_000
        except OSError:
            logger.warning(
                "SpaCy model not found. Install with: python -m spacy download en_core_web_sm"
            )
            logger.warning("Falling back to basic chunking")
            _nlp = "basic"
    return _nlp


def sent_tokenize(text: str) -> List[str]:
    """Sentence tokenizer using SpaCy with fallback."""
    nlp = get_nlp()
    if nlp == "basic":
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def chunk_text_semantic(
    text: str,
    max_words: int = 300,
    overlap_sentences: int = 2,
) -> List[str]:
    """
    Split text into chunks by grouping sentences without exceeding max_words per chunk.
    Adds overlap of sentences between chunks to preserve context.
    """
    sentences = sent_tokenize(text)
    if not sentences:
        return []

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_word_count = 0

    for sentence in sentences:
        sentence_word_count = len(sentence.split())

        if current_chunk and current_word_count + sentence_word_count > max_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = (
                current_chunk[-overlap_sentences:] if overlap_sentences > 0 else []
            )
            current_word_count = sum(len(s.split()) for s in current_chunk)

        current_chunk.append(sentence)
        current_word_count += sentence_word_count

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Legacy basic chunking for backwards compatibility."""
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if overlap < 0:
        raise ValueError("overlap must be >= 0")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: List[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(text[start:end])
        if end >= text_length:
            break
        start += chunk_size - overlap

    return chunks
