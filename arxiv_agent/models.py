from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel


class PaperMetadata(BaseModel):
    """Normalized metadata model for an arXiv paper."""

    arxiv_id: str
    title: Optional[str] = None
    authors: List[str] = []
    summary: Optional[str] = None
    published: Optional[datetime] = None
    pdf_url: Optional[str] = None
    raw: Optional[Any] = None


class IngestResult(BaseModel):
    """Result of ingesting a single paper."""

    meta: PaperMetadata
    pdf_path: str
    text_path: str
    success: bool = True
    error: Optional[str] = None

