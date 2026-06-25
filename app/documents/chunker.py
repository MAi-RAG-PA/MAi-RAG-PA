# ~/MAi-RAG/app/documents/chunker.py
import spacy
import logging
from typing import List

logger = logging.getLogger(__name__)

# Lazy load SpaCy model
_nlp = None

def get_nlp():
    """Lazy load SpaCy model to avoid startup overhead"""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
            _nlp.max_length = 18000000
        except OSError:
            logger.warning("SpaCy model not found. Install with: python -m spacy download en_core_web_sm")
            logger.warning("Falling back to basic chunking")
            _nlp = "basic"
    return _nlp

def sent_tokenize(text: str) -> List[str]:
    """Sentence tokenizer using SpaCy with fallback"""
    nlp = get_nlp()
    if nlp == "basic":
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

def chunk_text_semantic(text: str, max_words: int = 300, overlap_sentences: int = 2) -> List[str]:
    """
    Split text into chunks by grouping sentences without exceeding max_words per chunk.
    Adds overlap of sentences between chunks to preserve context.
    """
    sentences = sent_tokenize(text)
    if not sentences:
        return []
    
    chunks = []
    current_chunk = []
    current_word_count = 0

    for i, sentence in enumerate(sentences):
        sentence_word_count = len(sentence.split())
        
        if current_word_count + sentence_word_count > max_words and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = current_chunk[-overlap_sentences:] if overlap_sentences <= len(current_chunk) else []
            current_word_count = sum(len(s.split()) for s in current_chunk)
        
        current_chunk.append(sentence)
        current_word_count += sentence_word_count

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Legacy basic chunking for backwards compatibility"""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks
