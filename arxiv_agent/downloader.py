"""Downloader utilities for arxiv-agent.

This module provides a small, reusable async PDF downloader with retry/backoff.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import httpx
import aiofiles
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class DownloadError(Exception):
    pass


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type(Exception))
async def download_pdf(url: str, dest: Path, client: Optional[httpx.AsyncClient] = None) -> Path:
    """Download a PDF from `url` into `dest` (Path).

    - Writes to a temporary `.part` file and atomically replaces the destination on success.
    - Retries on exceptions using tenacity.
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=60.0)
        close_client = True

    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()

        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(tmp, "wb") as f:
            async for chunk in resp.aiter_bytes():
                await f.write(chunk)

        # Move to final destination atomically
        os.replace(str(tmp), str(dest))
        return dest

    except Exception as exc:
        raise DownloadError(f"failed to download {url}: {exc}") from exc

    finally:
        if close_client:
            await client.aclose()
