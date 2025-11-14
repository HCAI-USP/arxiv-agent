import marimo

__generated_with = "0.17.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # arxiv-agent — Marimo demo

    This demo notebook shows the main features of the `arxiv-agent` package in a lightweight, runnable Python script using Marimo-style cells.

    Sections:
      - setup
      - basic download
      - ingestion
      - DB inspection
      - embeddings (async + sync)
      - CLI examples, and testing
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1) Setup

    Install with Poetry (recommended) or pip in a virtual environment. The project uses Poetry in its `pyproject.toml`.

    ```bash
    poetry install
    poetry shell
    ```

    If you prefer pip for a quick trial, create a venv and install the package requirements (see `pyproject.toml`).
    """)
    return


@app.cell
def _():
    # 2) Imports: quick interactive helpers
    import asyncio
    from pathlib import Path

    import nest_asyncio

    # high-level helpers exposed by the package
    from arxiv_agent import ingest_query, download_pdf, extract_text, search_arxiv
    from arxiv_agent.embeddings import embed_paper, embed_paper_sync, embed_missing
    from arxiv_agent.db import (
        init_db,
        get_paper_by_arxiv_id,
        get_embeddings_for_paper,
    )
    from arxiv_agent.models import PaperMetadata

    print("imports OK")

    nest_asyncio.apply()
    return (
        Path,
        asyncio,
        download_pdf,
        embed_paper,
        embed_paper_sync,
        get_embeddings_for_paper,
        get_paper_by_arxiv_id,
        ingest_query,
        init_db,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3) Download a single paper (async)

    Use `download_pdf` to fetch a paper by URL and save it locally. This example is asynchronous and safe to run in a normal Python script.
    """)
    return


@app.cell
def _(Path, asyncio, download_pdf):
    async def demo_download():
        url = "https://arxiv.org/pdf/2101.00001.pdf"
        dest = Path("downloads/2101.00001.pdf")
        dest.parent.mkdir(parents=True, exist_ok=True)
        await download_pdf(url, dest)
        print("saved ->", dest)


    # Run example interactively when ready:
    asyncio.run(demo_download())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4) Ingest (search -> download -> extract)

    `ingest_query` performs a search on arXiv, downloads PDFs, extracts text (PyMuPDF), and optionally persists metadata into the SQLite DB when you pass `db_path`.

    Example: run a short ingestion and persist metadata for later embedding.
    """)
    return


@app.cell
def _(asyncio, ingest_query):
    async def demo_ingest():
        # Searches arXiv and writes downloads + extracted text into 'downloads/'
        results = await ingest_query(
            "quantum computing",
            max_results=2,
            output_dir="downloads",
            db_path="data/arxiv.db",
        )
        print("ingested:", len(results))
        for r in results:
            meta = r.get("meta")
            print("-", meta.arxiv_id, meta.title)


    # Run interactively: 
    asyncio.run(demo_ingest())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5) Database inspection

    After ingesting with `--db` or passing `db_path` to `ingest_query`, the SQLite DB stores papers and embeddings. Use the package DB helpers to inspect entries.
    """)
    return


@app.cell
def _(asyncio, get_embeddings_for_paper, get_paper_by_arxiv_id, init_db):
    async def db_inspect():
        await init_db("data/arxiv.db")  # idempotent init
        # retrieve a known paper by arXiv id
        paper = await get_paper_by_arxiv_id("data/arxiv.db", "2101.00001")
        print("paper row ->", paper)
        # list embeddings for a paper_id (if present)
        if paper:
            embs = await get_embeddings_for_paper("data/arxiv.db", paper["id"])
            print("embeddings for paper:", embs)

    # Run interactively: 
    asyncio.run(db_inspect())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6) Embeddings — async and sync usage

    `embed_paper` is async and returns a dict with `embedding_id` and optional `chroma_id`. A convenience `embed_paper_sync` is available for scripts (it will raise if called inside an event loop).

    You can also run a batch pass using the CLI `--embed` or programmatically with `embed_missing(...)` which supports `batch_size` and `delay` to help with rate limits.
    """)
    return


@app.cell
def _(Path, asyncio, embed_paper, embed_paper_sync):
    async def demo_embed_async():
        # embed a single paper (async)
        res = await embed_paper(
            "data/arxiv.db",
            paper_id=1,
            arxiv_id="2101.00001",
            text_path=Path("downloads/texts/2101.00001.txt"),
            backend="local",
            model="all-MiniLM-L6-v2",
        )
        print("embed result ->", res)


    def demo_embed_sync():
        # convenience sync wrapper (not for use inside running event loops)
        res = embed_paper_sync(
            "data/arxiv.db",
            paper_id=1,
            arxiv_id="2101.00001",
            text_path=Path("downloads/texts/2101.00001.txt"),
            backend="local",
        )
        print("embed result (sync) ->", res)


    # Run examples interactively:
    asyncio.run(demo_embed_async())
    demo_embed_sync()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7) Batch embeddings programmatically

    `embed_missing(db_path, batch_size=N, delay=secs)` will process pending papers in batches of `N` with an optional `delay` between batches. This is useful for OpenAI rate limits.
    """)
    return


@app.cell
def _():
    # run batch embedding (sync wrapper) — this calls the async pipeline under the hood
    # res = embed_missing('data/arxiv.db', backend='openai', model='text-embedding-3-small', chroma_dir=None, batch_size=5, delay=1.0)
    # print('batch embed results count ->', len(res))
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()
