"""Embedding pipeline: compute embeddings and optionally store them in Chroma.

Functions here are intentionally small and testable. They use the `nlp` helpers
and the DB helpers to persist embedding vectors and references.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict, Any

from .nlp import clean_text, get_embedding
from .db import save_embedding, get_paper_by_arxiv_id


def _load_text(text_path: str | Path) -> str:
    p = Path(text_path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def _get_chroma_client(persist_directory: Optional[str] = None):
    try:
        import chromadb
        from chromadb.config import Settings
    except Exception as exc:
        raise RuntimeError("chromadb is required for Chroma integration") from exc

    settings = Settings(persist_directory=persist_directory) if persist_directory else Settings()
    client = chromadb.Client(settings)
    return client


async def embed_paper(db_path: str | Path, paper_id: int, arxiv_id: str, text_path: str | Path, backend: str = "openai", model: Optional[str] = None, chroma_dir: Optional[str] = None) -> Dict[str, Any]:
    """Compute embedding for a paper's text, store it in DB and optionally in Chroma.

    Returns a dict with embedding id and chroma id (if stored).
    """
    text = _load_text(text_path)
    text = clean_text(text)
    # choose default models if not provided
    model_name = model or ("text-embedding-3-small" if backend == "openai" else "all-MiniLM-L6-v2")
    vec = get_embedding(text, backend=backend, model=model_name)

    emb_id = await save_embedding(db_path, paper_id, model_name, vec)

    chroma_id = None
    if chroma_dir:
        client = _get_chroma_client(chroma_dir)
        collection = client.get_or_create_collection(name="arxiv_agent")
        # use embedding id as the external id
        ext_id = f"paper-{paper_id}-emb-{emb_id}"
        collection.add(ids=[ext_id], embeddings=[vec], metadatas=[{"arxiv_id": arxiv_id}], documents=[text[:1000]])
        chroma_id = ext_id

    return {"embedding_id": emb_id, "chroma_id": chroma_id}


def embed_paper_sync(db_path: str | Path, paper_id: int, arxiv_id: str, text_path: str | Path, backend: str = "openai", model: Optional[str] = None, chroma_dir: Optional[str] = None) -> Dict[str, Any]:
    """Synchronous wrapper for `embed_paper`.

    Runs the async `embed_paper` coroutine via `asyncio.run` when no event loop is running.
    If called from a running event loop, raises a RuntimeError and suggests using the
    async function directly.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        raise RuntimeError(
            "embed_paper_sync cannot be called from a running event loop; use `await embed_paper(...)` instead."
        )

    return asyncio.run(embed_paper(db_path, paper_id, arxiv_id, text_path, backend=backend, model=model, chroma_dir=chroma_dir))


def embed_missing(
    db_path: str | Path,
    backend: str = "openai",
    model: Optional[str] = None,
    chroma_dir: Optional[str] = None,
    limit: Optional[int] = None,
    batch_size: Optional[int] = None,
    delay: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Find papers without embeddings and compute/store embeddings for them.

    Supports optional batching to help with rate limits and memory. If `batch_size`
    is provided, papers are processed in chunks of that size. An optional `delay`
    (seconds) can be provided to wait between batches.

    Returns list of results for each paper processed.
    """
    import asyncio
    from .db import papers_without_embeddings

    async def _run():
        pending = await papers_without_embeddings(db_path)
        if limit:
            pending = pending[:limit]
        results = []
        total = len(pending)
        # If no batching requested, process all sequentially
        if not batch_size or batch_size <= 0:
            for p in pending:
                res = await embed_paper(db_path, p["id"], p["arxiv_id"], p["text_path"], backend=backend, model=model, chroma_dir=chroma_dir)
                results.append({"paper_id": p["id"], "arxiv_id": p["arxiv_id"], **res})
            return results

        # Process in batches
        for start in range(0, total, batch_size):
            batch = pending[start : start + batch_size]
            for p in batch:
                res = await embed_paper(db_path, p["id"], p["arxiv_id"], p["text_path"], backend=backend, model=model, chroma_dir=chroma_dir)
                results.append({"paper_id": p["id"], "arxiv_id": p["arxiv_id"], **res})
            # delay between batches if requested
            if delay and (start + batch_size) < total:
                await asyncio.sleep(delay)

        return results

    return asyncio.run(_run())
