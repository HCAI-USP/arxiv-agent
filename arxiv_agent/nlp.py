"""Minimal NLP utilities: cleaning, tokenization, and embeddings.

This module provides small, testable helpers and two embedding backends:
- OpenAI (requires OPENAI_API_KEY)
- local sentence-transformers (optional)

The embedding functions are lazy and will raise informative errors if the
required libraries or keys are not available.
"""
from __future__ import annotations

import os
import re
from typing import List


def clean_text(text: str) -> str:
    """Basic cleaning: normalize whitespace and remove weird control chars."""
    if text is None:
        return ""
    # Replace non-breaking spaces and control chars
    text = text.replace("\xa0", " ")
    # Normalize line endings and collapse multiple spaces
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    # Strip excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize(text: str) -> List[str]:
    """Very small tokenizer splitting on whitespace and punctuation."""
    if not text:
        return []
    # keep words and simple punctuation splitting
    tokens = re.findall(r"\w+", text)
    return tokens


def get_embedding_openai(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """Get embedding from OpenAI. Requires OPENAI_API_KEY environment variable."""
    try:
        import openai
    except Exception as e:
        raise RuntimeError("openai package is required for OpenAI embeddings") from e

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment")
    openai.api_key = api_key

    resp = openai.Embedding.create(input=text, model=model)
    return resp["data"][0]["embedding"]


def get_embedding_local(text: str, model_name: str = "all-MiniLM-L6-v2") -> List[float]:
    """Get embedding using sentence-transformers installed locally.

    This function lazily imports SentenceTransformer and will raise a clear
    error if the package is not installed.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError("sentence-transformers is not installed; install it for local embeddings") from e

    model = SentenceTransformer(model_name)
    vec = model.encode(text)
    # ensure python float list
    return [float(x) for x in vec]


def get_embedding(text: str, backend: str = "openai", **kwargs) -> List[float]:
    """Unified embedding interface. backend is 'openai' or 'local'.

    Accepts `model` as a keyword to be compatible with both backends.
    """
    model = kwargs.get("model")
    if backend == "openai":
        return get_embedding_openai(text, model=model) if model else get_embedding_openai(text)
    if backend == "local":
        return get_embedding_local(text, model_name=model) if model else get_embedding_local(text)
    raise ValueError("unknown backend for embeddings")
