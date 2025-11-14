import asyncio
from pathlib import Path

import pytest

from arxiv_agent import embeddings as emb_mod
from arxiv_agent.db import init_db, upsert_paper, get_embeddings_for_paper
from arxiv_agent.models import PaperMetadata


def test_embed_missing_batched(tmp_path: Path, monkeypatch):
    db = tmp_path / "embed_int.db"
    # initialize DB
    asyncio.run(init_db(db))

    pids = []
    # create a few papers to embed
    for i in range(3):
        meta = PaperMetadata(arxiv_id=f"2101.int{i}", title=f"Title {i}")
        pid = asyncio.run(upsert_paper(db, meta, text_path=str(tmp_path / f"t{i}.txt")))
        pids.append(pid)
        (tmp_path / f"t{i}.txt").write_text(f"Text {i}", encoding="utf-8")

    # monkeypatch embedding and text loader to avoid external deps
    monkeypatch.setattr("arxiv_agent.embeddings.get_embedding", lambda text, backend, model=None: [0.1, 0.2, 0.3])
    monkeypatch.setattr("arxiv_agent.embeddings._load_text", lambda path: "cleaned text")

    # run embed_missing in batches of 1 (exercise batching code path)
    res = emb_mod.embed_missing(db, backend="local", model="m", chroma_dir=None, limit=None, batch_size=1, delay=0)
    assert isinstance(res, list)
    assert len(res) == 3

    # ensure embeddings were saved in DB
    for pid in pids:
        embs = asyncio.run(get_embeddings_for_paper(db, pid))
        assert len(embs) == 1
