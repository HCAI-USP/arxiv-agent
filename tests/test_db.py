import asyncio
from pathlib import Path

import pytest

from arxiv_agent.db import init_db, upsert_paper, get_paper_by_arxiv_id, set_processing, list_pending
from arxiv_agent.models import PaperMetadata


@pytest.mark.asyncio
async def test_db_upsert_and_query(tmp_path: Path):
    db = tmp_path / "test.db"
    await init_db(db)
    meta = PaperMetadata(arxiv_id="2101.00010", title="DB Paper", authors=["A"], summary="S")
    paper_id = await upsert_paper(db, meta, pdf_path=str(tmp_path / "p.pdf"), text_path=str(tmp_path / "t.txt"))
    assert isinstance(paper_id, int)
    rec = await get_paper_by_arxiv_id(db, "2101.00010")
    assert rec is not None
    assert rec["arxiv_id"] == "2101.00010"


@pytest.mark.asyncio
async def test_processing_and_list_pending(tmp_path: Path):
    db = tmp_path / "proc.db"
    await init_db(db)
    meta = PaperMetadata(arxiv_id="2101.00011", title="Proc Paper")
    pid = await upsert_paper(db, meta)
    await set_processing(db, pid, "extract", "pending")
    pending = await list_pending(db, stage="extract")
    assert any(p["arxiv_id"] == "2101.00011" for p in pending)
