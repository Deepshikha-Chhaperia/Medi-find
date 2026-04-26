"""Text cleaning and chunking utilities."""
from __future__ import annotations
import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalise unicode, collapse whitespace, strip control characters."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def count_tokens(text: str) -> int:
    """Rough whitespace-based token count (close to BPE for English/Hindi)."""
    return len(text.split())


def chunk_text(
    text: str,
    target_tokens: int = 300,
    overlap_tokens: int = 50,
) -> list[dict]:
    """
    Split text into semantically aware chunks.
    Strategy: split on paragraph/sentence boundaries, then combine to target size.
    Returns list of {chunk_text, chunk_index, token_count}.
    """
    # Split on paragraph boundaries first, then sentences
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_tokens: int = 0

    for para in paragraphs:
        para_tokens = count_tokens(para)

        # If a single paragraph exceeds target, split by sentence
        if para_tokens > target_tokens:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sent in sentences:
                sent_tokens = count_tokens(sent)
                if current_tokens + sent_tokens > target_tokens and current:
                    chunks.append(" ".join(current))
                    # Keep last N tokens for overlap
                    overlap_words = " ".join(current).split()[-overlap_tokens:]
                    current = [" ".join(overlap_words)]
                    current_tokens = len(overlap_words)
                current.append(sent)
                current_tokens += sent_tokens
        else:
            if current_tokens + para_tokens > target_tokens and current:
                chunks.append(" ".join(current))
                overlap_words = " ".join(current).split()[-overlap_tokens:]
                current = [" ".join(overlap_words)]
                current_tokens = len(overlap_words)
            current.append(para)
            current_tokens += para_tokens

    if current:
        chunks.append(" ".join(current))

    return [
        {"chunk_text": c, "chunk_index": i, "token_count": count_tokens(c), "page_number": 1}
        for i, c in enumerate(chunks)
        if c.strip()
    ]


def truncate_for_llm(text: str, max_tokens: int = 3000) -> str:
    """Truncate text to stay within LLM context limits."""
    words = text.split()
    if len(words) <= max_tokens:
        return text
    return " ".join(words[:max_tokens]) + "\n[... truncated ...]"
