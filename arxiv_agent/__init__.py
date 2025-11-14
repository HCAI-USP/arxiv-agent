"""arxiv_agent package

Public importable API for programmatic usage. Prefer importing the
high-level helpers from the package root::

	from arxiv_agent import ingest_query, download_pdf, PaperMetadata

Use ``asyncio.run`` to call the async helpers from synchronous code.
"""

from .models import IngestResult, PaperMetadata
from .downloader import DownloadError, download_pdf
from .ingest import ingest_query, search_arxiv, extract_text

__all__ = [
	"IngestResult",
	"PaperMetadata",
	"DownloadError",
	"download_pdf",
	"ingest_query",
	"search_arxiv",
	"extract_text",
]

__version__ = "0.1.0"


def ingest_query_sync(*args, **kwargs):
	"""Synchronous wrapper for `ingest_query`.

	Example: ingest_query_sync(query, max_results=2, output_dir="downloads", db_path="data.db")
	"""
	import asyncio

	return asyncio.run(ingest_query(*args, **kwargs))


def download_pdf_sync(*args, **kwargs):
	"""Synchronous wrapper for `download_pdf`."""
	import asyncio

	return asyncio.run(download_pdf(*args, **kwargs))


def get_embedding_sync(text: str, backend: str = "openai", **kwargs):
	import asyncio
	from .nlp import get_embedding

	return asyncio.run(asyncio.to_thread(get_embedding, text, backend, **kwargs))

