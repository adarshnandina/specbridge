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
def _root(verbose: bool = typer.Option(False, "--verbose", "-v", help="Log to stdout")) -> None:
    # Full JSON logs always go to logs/app.jsonl; stdout only shows warnings unless --verbose.
    setup_logging(stdout_level=None if verbose else "WARNING")


@app.command()
def ingest(
    directory: Path = typer.Argument(..., exists=True, file_okay=False),
    index: str = typer.Option(None, help="Index name (default: DEFAULT_INDEX)"),
    strategy: str = typer.Option(None, help="fixed | layout (default: CHUNK_STRATEGY)"),
    reingest: bool = typer.Option(False, help="Rebuild chunks for already-ingested documents"),
    context_header: bool = typer.Option(
        None,
        "--context-header/--no-context-header",
        help="Prefix chunks with a context header (default: on for layout, off for fixed)",
    ),
) -> None:
    """Ingest every PDF under DIRECTORY."""
    from specbridge.ingestion.chunking import ChunkOptions
    from specbridge.ingestion.pipeline import ingest_directory

    s = get_settings()
    strat = strategy or s.chunk_strategy
    opts = ChunkOptions(
        strategy=strat,
        context_header=(strat == "layout") if context_header is None else context_header,
    )
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


eval_app = typer.Typer(help="Evaluation framework", no_args_is_help=True)
app.add_typer(eval_app, name="eval")


@eval_app.command("run")
def eval_run(
    suite: str = typer.Option("retrieval", help="retrieval|qa|extraction|agent|all"),
    split: str = typer.Option("dev", help="dev|test"),
    config: Path = typer.Option(None, help="experiments/<x>.yaml"),
    tag: str = typer.Option("run", help="Run tag (part of the run id)"),
    use_cache: bool = typer.Option(False, "--use-cache", help="Use the LLM response cache"),
    provider: str = typer.Option(None, help="fake|anthropic|bedrock (default: LLM_PROVIDER)"),
    dry_run: bool = typer.Option(False, help="Only print the cost estimate"),
) -> None:
    """Run an evaluation suite and write eval_results/<run_id>.json/.md."""
    from specbridge.eval.runner import SUITES, EvalBudgetError, load_config, run_eval

    suites = list(SUITES) if suite == "all" else [suite]
    try:
        res = run_eval(
            suites,
            split,
            load_config(config),
            tag,
            use_cache=use_cache,
            provider=provider,
            dry_run=dry_run,
        )
    except (EvalBudgetError, RuntimeError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(2) from exc
    if not dry_run:
        console.print(f"run id: [bold]{res['run_id']}[/bold]  cost ${res['cost_usd']:.4f}")


@eval_app.command("compare")
def eval_compare(run_a: str, run_b: str) -> None:
    """Markdown comparison of two runs (deltas, CIs, within-noise flags)."""
    from specbridge.eval.compare import compare_runs, load_run

    console.print(compare_runs(load_run(run_a), load_run(run_b)))


@eval_app.command("set-baseline")
def eval_set_baseline(run: str) -> None:
    """Copy a run to eval_results/baseline.json."""
    import shutil

    from specbridge.eval.compare import load_run

    data = load_run(run)
    shutil.copyfile(Path("eval_results") / f"{data['run_id']}.json", "eval_results/baseline.json")
    console.print(f"baseline set to {data['run_id']}")


@eval_app.command("gate")
def eval_gate(
    baseline: Path = typer.Option(Path("eval_results/baseline.json"), help="Baseline run json"),
    candidate: str = typer.Option("latest", help="Run json path/run id, or 'latest'"),
    suite: str = typer.Option(None, help="Only check this suite (retrieval|qa|extraction|agent)"),
    tag: str = typer.Option(None, help="With --candidate latest: only runs with this tag"),
    thresholds: Path = typer.Option(Path("eval/thresholds.yaml")),
    allow_dataset_change: bool = typer.Option(
        False, help="Compare despite different dataset hashes"
    ),
) -> None:
    """Fail (exit 1) if the candidate regresses against the baseline beyond eval/thresholds.yaml."""
    from specbridge.eval.gate import run_gate

    try:
        ok, report = run_gate(
            baseline, candidate, thresholds, [suite] if suite else None, tag, allow_dataset_change
        )
    except (FileNotFoundError, KeyError) as exc:
        console.print(f"[red]gate error: {exc}[/red]")
        raise typer.Exit(2) from exc
    console.print(report)
    raise typer.Exit(0 if ok else 1)


@eval_app.command("validate-datasets")
def eval_validate() -> None:
    """Validate eval/datasets/*."""
    from specbridge.eval.datasets import validate_datasets

    problems = validate_datasets()
    for p in problems:
        console.print(f"[red]{p}[/red]")
    console.print("datasets OK" if not problems else f"{len(problems)} problems")
    if problems:
        raise typer.Exit(1)


agent_app = typer.Typer(help="Part-substitution agent", no_args_is_help=True)
app.add_typer(agent_app, name="agent")
logs_app = typer.Typer(help="Application logs", no_args_is_help=True)
app.add_typer(logs_app, name="logs")


@agent_app.command("resume")
def agent_resume(run_id: str = typer.Argument(..., help="Agent run id")) -> None:
    """Explicitly resume a run from its last persisted state (never automatic on startup)."""
    import uuid

    from specbridge.agent.runner import AgentRunner
    from specbridge.api.deps import get_erp
    from specbridge.api.routers.query import get_llm
    from specbridge.auth.api_keys import Principal
    from specbridge.db.session import session_scope
    from specbridge.errors import AppError

    try:
        with session_scope() as db:
            run = AgentRunner(db, get_llm(), get_erp()).resume(
                uuid.UUID(run_id), Principal("cli", "admin")
            )
            console.print(f"run {run.id}: state={run.state} error={run.error or '-'}")
    except (AppError, ValueError) as exc:
        console.print(f"[red]{getattr(exc, 'message', exc)}[/red]")
        raise typer.Exit(1) from exc


@agent_app.command("show")
def agent_show(run_id: str) -> None:
    """Print a run's state and steps."""
    import uuid

    from sqlalchemy import select

    from specbridge.db.models import AgentRun, AgentStep
    from specbridge.db.session import session_scope

    with session_scope() as db:
        run = db.get(AgentRun, uuid.UUID(run_id))
        if run is None:
            console.print("[red]run not found[/red]")
            raise typer.Exit(1)
        console.print(f"{run.id} state={run.state} requested_by={run.requested_by}")
        t = Table("#", "state", "tool", "status", "ms", "error")
        for st in db.scalars(
            select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.step_no)
        ):
            t.add_row(
                str(st.step_no),
                st.state,
                st.tool_name or "",
                st.status,
                str(st.latency_ms),
                (st.error or "")[:50],
            )
        console.print(t)


@logs_app.command("tail")
def logs_tail(
    event: str = typer.Option(None, "--event", "-e", help="Glob on the event name, e.g. 'agent.*'"),
    lines: int = typer.Option(20, "--lines", "-n"),
    follow: bool = typer.Option(False, "--follow", "-f"),
    file: Path = typer.Option(None, help="Log file (default: LOG_DIR/app.jsonl)"),
) -> None:
    """Show recent structured log lines, optionally filtered by event pattern."""
    import fnmatch
    import json
    import time

    path = file or (get_settings().log_dir / "app.jsonl")
    if not path.exists():
        console.print(f"[red]no log file at {path}[/red]")
        raise typer.Exit(1)

    def match(line: str) -> bool:
        if not event:
            return True
        try:
            return fnmatch.fnmatch(str(json.loads(line).get("event", "")), event)
        except ValueError:
            return False

    with path.open(encoding="utf-8") as fh:
        recent = [ln for ln in fh if match(ln)][-lines:]
        for ln in recent:
            typer.echo(ln.rstrip())
        while follow:
            ln = fh.readline()
            if not ln:
                time.sleep(0.5)
            elif match(ln):
                typer.echo(ln.rstrip())


if __name__ == "__main__":
    app()
