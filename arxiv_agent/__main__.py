"""Simple CLI entrypoint for arxiv-agent.

Provides a minimal --dry-run and --id based fetch that demonstrates the downloader.
"""
import argparse
import asyncio
import sys
from pathlib import Path
from rich.console import Console

from .downloader import download_pdf
from .ingest import ingest_query
from .embeddings import embed_missing

console = Console()


async def _download_mode(arxiv_id: str, output: str, dry_run: bool) -> int:
    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] would fetch id={arxiv_id} and save to {output}")
        return 0

    if not arxiv_id:
        console.print("[red]No arXiv id provided. Use --id to specify one.[/red]")
        return 2

    dest = Path(output) / f"{arxiv_id}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        await download_pdf(url, dest)
        console.print(f"[green]Downloaded:[/green] {dest}")
        return 0
    except Exception as exc:
        console.print(f"[red]Error downloading:[/red] {exc}")
        return 1


async def _ingest_mode(query: str, max_results: int, output: str, dry_run: bool, db_path: str | None = None) -> int:
    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] would ingest query='{query}' max_results={max_results} -> {output}")
        return 0

    try:
        results = await ingest_query(query, max_results=max_results, output_dir=output, db_path=db_path)
        console.print(f"[green]Ingested {len(results)} papers into[/green] {output}")
        for r in results:
            meta = r.get("meta")
            console.print(f"- {meta.arxiv_id}: {meta.title}")
        return 0
    except Exception as exc:
        console.print(f"[red]Ingest failed:[/red] {exc}")
        return 1


async def _embed_mode(
    db_path: str,
    backend: str,
    model: str | None,
    chroma_dir: str | None,
    limit: int | None,
    batch_size: int | None = None,
    delay: float | None = None,
) -> int:
    try:
        results = embed_missing(db_path, backend=backend, model=model, chroma_dir=chroma_dir, limit=limit, batch_size=batch_size, delay=delay)
        console.print(f"[green]Embedded {len(results)} papers.[/green]")
        return 0
    except Exception as exc:
        console.print(f"[red]Embedding failed:[/red] {exc}")
        return 1


async def run(args: argparse.Namespace) -> int:
    if args.ingest:
        return await _ingest_mode(args.ingest, args.max_results, args.output, args.dry_run, db_path=args.db)
    if args.embed:
        return await _embed_mode(
            args.db,
            args.embed_backend,
            args.embed_model,
            args.chroma_dir,
            args.embed_limit,
            args.embed_batch_size,
            args.embed_batch_delay,
        )
    return await _download_mode(args.id, args.output, args.dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(prog="arxiv-agent")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without downloading")
    parser.add_argument("--id", help="arXiv id (e.g., 2101.00001)")
    parser.add_argument("--ingest", help="Run ingestion for a query string (mutually exclusive with --id)")
    parser.add_argument("--db", default=None, help="Path to sqlite DB file to persist metadata and embeddings")
    parser.add_argument("--embed", action="store_true", help="Compute embeddings for papers missing them in the DB")
    parser.add_argument("--embed-backend", default="openai", help="Embedding backend: openai or local")
    parser.add_argument("--embed-model", default=None, help="Embedding model to use")
    parser.add_argument("--embed-limit", type=int, default=None, help="Limit number of papers to embed in one run")
    parser.add_argument("--embed-batch-size", type=int, default=None, help="Batch size for embeddings to help with rate limits")
    parser.add_argument("--embed-batch-delay", type=float, default=None, help="Delay in seconds between embedding batches")
    parser.add_argument("--chroma-dir", default=None, help="Directory to persist Chroma DB (optional)")
    parser.add_argument("--max-results", type=int, default=5, help="Max results for ingestion")
    parser.add_argument("--output", default="downloads", help="Output directory")
    args = parser.parse_args()

    # Simple exclusivity: either --ingest or --id
    if args.ingest and args.id:
        console.print("[red]Specify either --ingest or --id (not both).[/red]")
        sys.exit(2)

    if args.embed and not args.db:
        console.print("[red]Embedding requires --db to point to a sqlite database file.[/red]")
        sys.exit(2)

    exit_code = asyncio.run(run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
