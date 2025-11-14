# arxiv-agent
AI agent to download and structure papers and data from arXiv

## Usage

This repository provides a minimal agent to search arXiv, download PDFs, and extract text.

CLI examples (after installing with Poetry):

Dry-run download by arXiv id:

```bash
poetry run arxiv-agent --dry-run --id 2101.00001
```

Download a paper by id:

```bash
poetry run arxiv-agent --id 2101.00001 --output downloads
```

Run ingestion for a query (search -> download -> extract):

```bash
poetry run arxiv-agent --ingest "quantum computing" --max-results 5 --output downloads
```

Dry-run ingestion:

```bash
poetry run arxiv-agent --ingest "quantum computing" --max-results 2 --dry-run
```

The ingestion pipeline will write PDFs to `downloads/` and extracted text to `downloads/texts/`.

Persists metadata and embeddings: to persist metadata into the SQLite DB during ingestion, pass the `--db` flag when running `--ingest`. This will create/initialize the database and store paper metadata and text paths so you can later run `--embed` against the same DB.

Example:

```bash
poetry run arxiv-agent --ingest "quantum computing" --max-results 5 --output downloads --db data/arxiv.db
```

## Library usage (importable API)

You can import and use the package programmatically. Example (async):

```python
import asyncio
from arxiv_agent import ingest_query

async def main():
	results = await ingest_query("machine learning", max_results=2, output_dir="downloads")
	for r in results:
		meta = r["meta"]
		print(meta.arxiv_id, meta.title)

asyncio.run(main())
```

Download a single paper programmatically:

```python
import asyncio
from pathlib import Path
from arxiv_agent import download_pdf

async def fetch_one():
	url = "https://arxiv.org/pdf/2101.00001.pdf"
	dest = Path("downloads/2101.00001.pdf")
	await download_pdf(url, dest)

asyncio.run(fetch_one())
```

Note: the package exposes the high-level helpers at the package root for convenience:
`ingest_query`, `search_arxiv`, `download_pdf`, `extract_text`, `PaperMetadata`.


## Embeddings

The package includes a small embedding pipeline. You can compute embeddings for papers stored in the SQLite DB and optionally persist vectors to a local Chroma collection.

CLI example — compute embeddings for papers missing them in the DB:

```bash
# requires a populated sqlite DB (use --db when ingesting or set up separately)
poetry run arxiv-agent --embed --db data/arxiv.db --embed-backend openai --embed-model text-embedding-3-small --chroma-dir ./chroma
```

Programmatic usage (async):

```python
import asyncio
from pathlib import Path
from arxiv_agent.embeddings import embed_paper

async def run_one():
	# embed a single paper by id (paper_id from the DB)
	res = await embed_paper("data/arxiv.db", paper_id=1, arxiv_id="2101.00001", text_path=Path("downloads/texts/2101.00001.txt"), backend="local", model="all-MiniLM-L6-v2")
	print(res)

asyncio.run(run_one())
```

Programmatic usage (sync helper):

If you prefer a synchronous call from a script, use the provided sync wrapper `embed_paper_sync`:

```python
from pathlib import Path
from arxiv_agent.embeddings import embed_paper_sync

res = embed_paper_sync("data/arxiv.db", paper_id=1, arxiv_id="2101.00001", text_path=Path("downloads/texts/2101.00001.txt"), backend="local")
print(res)
```

Notes:
- OpenAI backend requires the `OPENAI_API_KEY` environment variable.
- Local backend requires `sentence-transformers` to be installed.
- The CLI `--embed` command uses the DB path provided via `--db` and will process papers missing embeddings.


