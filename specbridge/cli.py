"""`specbridge` command line interface."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from specbridge.config import get_settings
from specbridge.logging_setup import setup_logging

app = typer.Typer(help="SpecBridge CLI", no_args_is_help=True)
console = Console()


@app.callback()
def _root() -> None:
    setup_logging()


@app.command()
def ingest(
    directory: Path = typer.Argument(..., exists=True, file_okay=False),
    index: str = typer.Option(None, help="Index name (default: DEFAULT_INDEX)"),
    strategy: str = typer.Option(None, help="fixed | layout (default: CHUNK_STRATEGY)"),
    reingest: bool = typer.Option(False, help="Rebuild chunks for already-ingested documents"),
    context_header: bool = typer.Option(True, help="Prefix chunks with a context header"),
) -> None:
    """Ingest every PDF under DIRECTORY."""
    from specbridge.ingestion.chunking import ChunkOptions
    from specbridge.ingestion.pipeline import ingest_directory

    s = get_settings()
    opts = ChunkOptions(strategy=strategy or s.chunk_strategy, context_header=context_header)
    results = ingest_directory(
        directory, index=index or s.default_index, opts=opts, reingest=reingest
    )
    t = Table("file", "status", "pages", "chunks", "tables", "seconds", "error")
    for r in results:
        t.add_row(
            r.filename,
            r.status,
            str(r.pages),
            str(r.chunks),
            str(r.tables),
            f"{r.duration_s:.2f}",
            (r.error or "")[:60],
        )
    console.print(t)
    failed = [r for r in results if r.status == "failed"]
    console.print(f"{len(results)} files, {len(failed)} failed")
    if failed:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
