"""Simple async SQLite DB helpers for arxiv-agent.

This module provides tiny convenience functions around `aiosqlite` to store
paper metadata, processing status, and simple query helpers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict, Any

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY,
    arxiv_id TEXT UNIQUE,
    title TEXT,
    authors TEXT,
    summary TEXT,
    published TIMESTAMP,
    pdf_path TEXT,
    text_path TEXT,
    raw_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processing (
    id INTEGER PRIMARY KEY,
    paper_id INTEGER,
    stage TEXT,
    status TEXT,
    error TEXT,
    tried_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(paper_id) REFERENCES papers(id)
);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY,
    paper_id INTEGER,
    model TEXT,
    vector_json TEXT,
    chroma_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(paper_id) REFERENCES papers(id)
);
"""


async def init_db(db_path: str | Path) -> None:
    db_path = str(db_path)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def upsert_paper(db_path: str | Path, metadata: Any, pdf_path: Optional[str] = None, text_path: Optional[str] = None) -> int:
    """Insert or update a paper by `arxiv_id`. Returns the paper id."""
    db_path = str(db_path)
    authors_json = json.dumps(metadata.authors if getattr(metadata, "authors", None) is not None else [])
    raw_json = json.dumps(getattr(metadata, "raw", None))
    published = getattr(metadata, "published", None)
    published_val = published.isoformat() if published is not None else None

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO papers (arxiv_id, title, authors, summary, published, pdf_path, text_path, raw_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                metadata.arxiv_id,
                getattr(metadata, "title", None),
                authors_json,
                getattr(metadata, "summary", None),
                published_val,
                pdf_path,
                text_path,
                raw_json,
            ),
        )
        # update fields if provided or to refresh raw/title
        await db.execute(
            "UPDATE papers SET title = ?, authors = ?, summary = ?, published = ?, pdf_path = COALESCE(?, pdf_path), text_path = COALESCE(?, text_path), raw_json = ?, updated_at = CURRENT_TIMESTAMP WHERE arxiv_id = ?",
            (
                getattr(metadata, "title", None),
                authors_json,
                getattr(metadata, "summary", None),
                published_val,
                pdf_path,
                text_path,
                raw_json,
                metadata.arxiv_id,
            ),
        )
        await db.commit()
        cur = await db.execute("SELECT id FROM papers WHERE arxiv_id = ?", (metadata.arxiv_id,))
        row = await cur.fetchone()
        return int(row[0])


async def get_paper_by_arxiv_id(db_path: str | Path, arxiv_id: str) -> Optional[Dict[str, Any]]:
    db_path = str(db_path)
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute("SELECT id, arxiv_id, title, authors, summary, published, pdf_path, text_path, raw_json, created_at, updated_at FROM papers WHERE arxiv_id = ?", (arxiv_id,))
        row = await cur.fetchone()
        if not row:
            return None
        authors = json.loads(row[3]) if row[3] else []
        raw = json.loads(row[8]) if row[8] else None
        return {
            "id": row[0],
            "arxiv_id": row[1],
            "title": row[2],
            "authors": authors,
            "summary": row[4],
            "published": row[5],
            "pdf_path": row[6],
            "text_path": row[7],
            "raw": raw,
            "created_at": row[9],
            "updated_at": row[10],
        }


async def set_processing(db_path: str | Path, paper_id: int, stage: str, status: str, error: Optional[str] = None) -> None:
    db_path = str(db_path)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO processing (paper_id, stage, status, error) VALUES (?, ?, ?, ?)",
            (paper_id, stage, status, error),
        )
        await db.commit()


async def list_pending(db_path: str | Path, stage: str = "extract") -> list[Dict[str, Any]]:
    db_path = str(db_path)
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            "SELECT p.id, p.arxiv_id, p.title, p.pdf_path, p.text_path FROM papers p JOIN processing pr ON pr.paper_id = p.id WHERE pr.stage = ? AND pr.status = 'pending'",
            (stage,),
        )
        rows = await cur.fetchall()
        return [
            {"id": r[0], "arxiv_id": r[1], "title": r[2], "pdf_path": r[3], "text_path": r[4]} for r in rows
        ]


async def save_embedding(db_path: str | Path, paper_id: int, model: str, vector: list[float]) -> int:
    db_path = str(db_path)
    vec_json = json.dumps(vector)
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            "INSERT INTO embeddings (paper_id, model, vector_json) VALUES (?, ?, ?)", (paper_id, model, vec_json)
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_embeddings_for_paper(db_path: str | Path, paper_id: int) -> list[Dict[str, Any]]:
    db_path = str(db_path)
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute("SELECT id, model, vector_json, created_at FROM embeddings WHERE paper_id = ?", (paper_id,))
        rows = await cur.fetchall()
        return [
            {"id": r[0], "model": r[1], "vector": json.loads(r[2]), "created_at": r[3]} for r in rows
        ]


async def papers_without_embeddings(db_path: str | Path) -> list[Dict[str, Any]]:
    db_path = str(db_path)
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            "SELECT p.id, p.arxiv_id, p.title, p.text_path FROM papers p LEFT JOIN embeddings e ON e.paper_id = p.id WHERE e.id IS NULL"
        )
        rows = await cur.fetchall()
        return [{"id": r[0], "arxiv_id": r[1], "title": r[2], "text_path": r[3]} for r in rows]
