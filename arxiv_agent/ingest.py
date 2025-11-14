"""Minimal ingestion pipeline for arxiv-agent.

This module provides:
- `search_arxiv` - async wrapper around the `arxiv` package to get metadata
- `extract_text` - extract text from a local PDF using PyMuPDF
- `ingest_query` - end-to-end flow: search -> download -> extract -> return results

The implementation keeps I/O async-friendly and small so it is easy to test.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import List, Dict, Any

import arxiv
import fitz  # PyMuPDF

from .models import PaperMetadata
from .downloader import download_pdf
from .db import init_db, upsert_paper, set_processing


_ARXIV_ID_RE = re.compile(r"([^/]+v?\d*)(?:\.pdf)?$")


def _extract_arxiv_id(entry_id: str) -> str:
    if not entry_id:
        return ""
    m = _ARXIV_ID_RE.search(entry_id)
    if m:
        return m.group(1)
    return entry_id.rstrip("/").split("/")[-1]


async def search_arxiv(query: str, max_results: int = 10) -> List[PaperMetadata]:
    """Search arXiv and return a list of normalized PaperMetadata.

    The `arxiv` package used here is synchronous, so we run it in a thread.
    """

    def _sync_search() -> List[Any]:
        search = arxiv.Search(query=query, max_results=max_results)
        return list(search.results())

    results = await asyncio.to_thread(_sync_search)
    metas: List[PaperMetadata] = []
    for r in results:
        # r is an arxiv.Result object; access attributes with fallbacks to be robust.
        entry_id = getattr(r, "entry_id", None) or getattr(r, "id", None) or ""
        arxiv_id = _extract_arxiv_id(entry_id)
        title = getattr(r, "title", None) or ""
        authors_raw = getattr(r, "authors", []) or []
        authors = [a.name if hasattr(a, "name") else str(a) for a in authors_raw]
        summary = getattr(r, "summary", None)
        published = getattr(r, "published", None)
        pdf_url = getattr(r, "pdf_url", f"https://arxiv.org/pdf/{arxiv_id}.pdf")

        meta = PaperMetadata(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            summary=summary,
            published=published,
            pdf_url=pdf_url,
            raw={"entry_id": entry_id},
        )
        metas.append(meta)

    return metas


def extract_text_sync(pdf_path: Path) -> str:
    """Extract plain text from a PDF file using PyMuPDF (synchronous)."""
    doc = fitz.open(str(pdf_path))
    parts: List[str] = []
    for page in doc:
        parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(parts)


async def extract_text(pdf_path: Path) -> str:
    return await asyncio.to_thread(extract_text_sync, pdf_path)


async def ingest_query(query: str, max_results: int = 10, output_dir: Path | str = "downloads", concurrency: int = 3, db_path: str | Path | None = None) -> List[Dict[str, Any]]:
    """End-to-end ingestion: search -> download PDFs -> extract text.

    Returns a list of result dictionaries containing `meta` (PaperMetadata),
    `pdf_path` (Path) and `text_path` (Path).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metas = await search_arxiv(query, max_results=max_results)

    if db_path:
        await init_db(db_path)

    # Deduplicate by arXiv id to avoid downloading the same paper twice.
    seen: set[str] = set()
    unique_metas: List[PaperMetadata] = []
    for m in metas:
        if m.arxiv_id not in seen:
            seen.add(m.arxiv_id)
            unique_metas.append(m)

    sem = asyncio.Semaphore(concurrency)

    async def _handle(meta: PaperMetadata) -> Dict[str, Any]:
        async with sem:
            pdf_path = output_dir / f"{meta.arxiv_id}.pdf"
            text_path = output_dir / "texts" / f"{meta.arxiv_id}.txt"
            text_path.parent.mkdir(parents=True, exist_ok=True)

            paper_id = None
            if db_path:
                # upsert before downloading so paper record exists
                paper_id = await upsert_paper(db_path, meta)
                await set_processing(db_path, paper_id, "download", "pending")
            try:
                # download
                url = meta.pdf_url or f"https://arxiv.org/pdf/{meta.arxiv_id}.pdf"
                await download_pdf(url, pdf_path)
                # extract
                text = await extract_text(pdf_path)
                text_path.write_text(text, encoding="utf-8")

                if db_path and paper_id:
                    # update record with paths and mark stages
                    await upsert_paper(db_path, meta, pdf_path=str(pdf_path), text_path=str(text_path))
                    await set_processing(db_path, paper_id, "download", "success")
                    await set_processing(db_path, paper_id, "extract", "success")

                return {"meta": meta, "pdf_path": pdf_path, "text_path": text_path, "success": True, "error": None}
            except Exception as exc:
                # Don't fail the whole ingestion run for one paper; record the error.
                if db_path and paper_id:
                    await set_processing(db_path, paper_id, "download", "error", error=str(exc))
                return {"meta": meta, "pdf_path": pdf_path, "text_path": text_path, "success": False, "error": str(exc)}

    tasks = [asyncio.create_task(_handle(m)) for m in unique_metas]
    results = await asyncio.gather(*tasks)
    return results
