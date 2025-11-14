import asyncio
from pathlib import Path

import pytest

from arxiv_agent.embeddings import embed_paper, embed_missing
from arxiv_agent.db import init_db, upsert_paper, get_paper_by_arxiv_id, get_embeddings_for_paper
from arxiv_agent.models import PaperMetadata


@pytest.mark.asyncio
async def test_embed_paper_monkeypatched(tmp_path: Path, monkeypatch):
    db = tmp_path / "embed.db"
    await init_db(db)
    meta = PaperMetadata(arxiv_id="2101.0embed", title="Embeddable")
    pid = await upsert_paper(db, meta, text_path=str(tmp_path / "t.txt"))
    (tmp_path / "t.txt").write_text("Some text to embed", encoding="utf-8")

    # monkeypatch get_embedding to return a small vector without calling external services
    monkeypatch.setattr("arxiv_agent.embeddings.get_embedding", lambda text, backend, model=None: [0.1, 0.2, 0.3])

    res = await embed_paper(db, pid, meta.arxiv_id, tmp_path / "t.txt", backend="local", model="m", chroma_dir=None)
    assert "embedding_id" in res
    emb = await get_embeddings_for_paper(db, pid)
    assert len(emb) == 1


def test_embed_missing_monkeypatched(tmp_path: Path, monkeypatch):
    db = tmp_path / "embed2.db"
    asyncio.run(init_db(db))
    meta = PaperMetadata(arxiv_id="2101.0embed2", title="Embeddable2")
    pid = asyncio.run(upsert_paper(db, meta, text_path=str(tmp_path / "t2.txt")))
    (tmp_path / "t2.txt").write_text("Text for embed", encoding="utf-8")

    monkeypatch.setattr("arxiv_agent.embeddings._load_text", lambda path: "cleaned text")
    monkeypatch.setattr("arxiv_agent.embeddings.get_embedding", lambda text, backend, model=None: [0.4, 0.5])

    res = embed_missing(db, backend="local", model="m", chroma_dir=None)
    assert isinstance(res, list)
    assert len(res) >= 1
