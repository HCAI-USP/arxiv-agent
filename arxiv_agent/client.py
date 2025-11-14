from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import ingest_query_sync, download_pdf_sync


class ArxivAgentClient:
    """Lightweight synchronous client wrapping common operations.

    Examples:
        client = ArxivAgentClient(output_dir="downloads", db_path="data.db")
        client.ingest("quantum computing", max_results=5)
    """

    def __init__(self, output_dir: str | Path = "downloads", db_path: Optional[str] = None) -> None:
        self.output_dir = str(output_dir)
        self.db_path = db_path

    def ingest(self, query: str, max_results: int = 5, dry_run: bool = False):
        return ingest_query_sync(query, max_results=max_results, output_dir=self.output_dir, concurrency=3, db_path=self.db_path) if not dry_run else None

    def fetch(self, arxiv_id: str):
        url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        dest = Path(self.output_dir) / f"{arxiv_id}.pdf"
        return download_pdf_sync(url, dest)
