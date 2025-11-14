import asyncio
from pathlib import Path

import pytest

from arxiv_agent.models import PaperMetadata


@pytest.mark.asyncio
async def test_ingest_query_monkeypatched(tmp_path: Path, monkeypatch):
    # Prepare a fake PaperMetadata list
    meta = PaperMetadata(arxiv_id="2101.00001", title="Test Paper", pdf_url="http://example.com/test.pdf")

    async def fake_search_arxiv(query, max_results=10):
        return [meta]

    async def fake_download_pdf(url, dest, client=None):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"%PDF-1.4 FAKEPDF")
        return dest

    async def fake_extract_text(pdf_path: Path):
        return "Extracted text"

    # Monkeypatch the search, download and extract functions in the ingest module
    import arxiv_agent.ingest as ingest

    monkeypatch.setattr(ingest, "search_arxiv", fake_search_arxiv)
    monkeypatch.setattr(ingest, "download_pdf", fake_download_pdf)
    monkeypatch.setattr(ingest, "extract_text", fake_extract_text)

    results = await ingest.ingest_query("test query", max_results=1, output_dir=tmp_path, concurrency=1)
    assert len(results) == 1
    r = results[0]
    assert r["meta"].arxiv_id == "2101.00001"
    assert r["pdf_path"].exists()
    assert r["text_path"].read_text(encoding="utf-8") == "Extracted text"


@pytest.mark.asyncio
async def test_ingest_duplicates(tmp_path: Path, monkeypatch):
    # Two entries with same arxiv_id should be deduplicated
    meta1 = PaperMetadata(arxiv_id="2101.00001", title="Paper A", pdf_url="http://example.com/a.pdf")
    meta2 = PaperMetadata(arxiv_id="2101.00001", title="Paper A duplicate", pdf_url="http://example.com/a_dup.pdf")

    async def fake_search_arxiv(query, max_results=10):
        return [meta1, meta2]

    download_calls = {"count": 0}

    async def fake_download_pdf(url, dest, client=None):
        download_calls["count"] += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"%PDF-1.4 FAKEPDF")
        return dest

    async def fake_extract_text(pdf_path: Path):
        return "Extracted text"

    import arxiv_agent.ingest as ingest

    monkeypatch.setattr(ingest, "search_arxiv", fake_search_arxiv)
    monkeypatch.setattr(ingest, "download_pdf", fake_download_pdf)
    monkeypatch.setattr(ingest, "extract_text", fake_extract_text)

    results = await ingest.ingest_query("test query", max_results=2, output_dir=tmp_path, concurrency=1)
    # Should deduplicate and only download once
    assert download_calls["count"] == 1
    assert len(results) == 1


@pytest.mark.asyncio
async def test_ingest_error_handling(tmp_path: Path, monkeypatch):
    # Two different papers; one download fails, the other succeeds
    meta_ok = PaperMetadata(arxiv_id="2101.00002", title="OK Paper", pdf_url="http://example.com/ok.pdf")
    meta_fail = PaperMetadata(arxiv_id="2101.00003", title="Bad Paper", pdf_url="http://example.com/bad.pdf")

    async def fake_search_arxiv(query, max_results=10):
        return [meta_ok, meta_fail]

    async def fake_download_pdf(url, dest, client=None):
        if "bad.pdf" in url:
            raise Exception("download error")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"%PDF-1.4 OKPDF")
        return dest

    async def fake_extract_text(pdf_path: Path):
        return "Extracted"

    import arxiv_agent.ingest as ingest

    monkeypatch.setattr(ingest, "search_arxiv", fake_search_arxiv)
    monkeypatch.setattr(ingest, "download_pdf", fake_download_pdf)
    monkeypatch.setattr(ingest, "extract_text", fake_extract_text)

    results = await ingest.ingest_query("test query", max_results=2, output_dir=tmp_path, concurrency=2)
    assert len(results) == 2
    statuses = {r["meta"].arxiv_id: r for r in results}
    assert statuses["2101.00002"]["success"] is True
    assert statuses["2101.00003"]["success"] is False
    assert "download error" in statuses["2101.00003"]["error"]
