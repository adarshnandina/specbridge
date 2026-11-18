"""Eval runner: suites, cost estimate, result files (json + md), run ids."""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from specbridge.config import Settings, get_settings
from specbridge.db.models import Chunk
from specbridge.db.session import session_scope
from specbridge.eval import metrics as M
from specbridge.eval.datasets import QAItem, dataset_hashes, load_qa
from specbridge.eval.judge import judge_answer
from specbridge.ingestion.embeddings import Embedder, get_embedder
from specbridge.llm.cache import ResponseCache
from specbridge.llm.fake_handlers import register_all_handlers
from specbridge.llm.fake_provider import FakeProvider
from specbridge.llm.pricing import compute_cost
from specbridge.llm.usage import (
    LLMService,
    MemoryLedger,
    build_provider,
    db_recorder,
    db_spent_today,
)
from specbridge.logging_setup import get_logger
from specbridge.qa.service import answer_question
from specbridge.retrieval.service import retrieve

log = get_logger("specbridge.eval")
RESULTS_DIR = Path("eval_results")
SUITES = ("retrieval", "qa", "extraction", "agent")


class EvalBudgetError(RuntimeError):
    pass


class RunConfig(BaseModel):
    name: str = "default"
    description: str = ""
    index_name: str | None = None
    retrieval: dict[str, Any] = Field(
        default_factory=dict
    )  # mode, top_k, rerank, include_superseded
    qa: dict[str, Any] = Field(default_factory=dict)  # min_score, top_k
    extraction: dict[str, Any] = Field(default_factory=dict)
    agent: dict[str, Any] = Field(default_factory=dict)


def load_config(path: str | Path | None) -> RunConfig:
    if not path:
        return RunConfig()
    return RunConfig.model_validate(yaml.safe_load(Path(path).read_text()) or {})


@dataclass
class SuiteContext:
    settings: Settings
    cfg: RunConfig
    split: str
    use_cache: bool
    provider_name: str
    embedder: Embedder | None = None
    llm: LLMService | None = None
    ledger: MemoryLedger | None = None
    max_cost: float = 2.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SuiteOutput:
    items: list[dict[str, Any]]
    aggregates: dict[str, Any]
    ops: dict[str, Any]
    cost_usd: float = 0.0
    models: dict[str, str] = field(default_factory=dict)
    prompt_versions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    aborted: bool = False


def git_sha() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip()
            or "nogit"
        )
    except Exception:
        return "nogit"


def make_llm(settings: Settings, provider_name: str, use_cache: bool) -> tuple[LLMService, Any]:
    s = settings.model_copy(update={"llm_provider": provider_name, "log_llm_payloads": False})
    provider = build_provider(s)
    if isinstance(provider, FakeProvider):
        register_all_handlers(provider)
    cache = ResponseCache(s.data_dir / "cache" / "llm_cache.sqlite") if use_cache else None
    if provider_name == "fake":
        ledger = MemoryLedger()
        from specbridge.llm.budget import BudgetGuard

        llm = LLMService(
            provider,
            settings=s,
            recorder=ledger.record,
            budget=BudgetGuard(s.llm_daily_budget_usd, ledger.spent),
            cache=cache,
        )
    else:
        from specbridge.llm.budget import BudgetGuard

        llm = LLMService(
            provider,
            settings=s,
            recorder=db_recorder,
            budget=BudgetGuard(s.llm_daily_budget_usd, db_spent_today),
            cache=cache,
        )
    return llm, provider


# ----------------------------------------------------------------- estimates
def estimate_cost(suite: str, n_items: int, ctx: SuiteContext) -> float:
    """Upper-bound cost estimate in USD (ignores cache hits). Fake provider is free."""
    if ctx.provider_name == "fake":
        return 0.0
    s = ctx.settings
    top_k = ctx.cfg.qa.get("top_k") or ctx.cfg.retrieval.get("top_k") or s.retrieval_top_k
    if suite == "qa":
        in_tok = 450 + top_k * 220 + 60
        per = compute_cost(s.model_for("qa"), in_tok, 220)
        judge = compute_cost(s.model_for("judge"), 600, 80) * 0.1
        return n_items * (per + judge)
    if suite == "extraction":
        return (
            n_items
            * compute_cost(ctx.cfg.extraction.get("model") or s.model_for("extraction"), 3000, 700)
            * 1.6
        )
    if suite == "agent":
        return n_items * 4 * compute_cost(s.model_for("agent_parse"), 1500, 300)
    return 0.0


# ------------------------------------------------------------------- suites
def _check_index(index: str) -> None:
    with session_scope() as s:
        n = s.scalar(select(func.count()).select_from(Chunk).where(Chunk.index_name == index))
    if not n:
        raise RuntimeError(f"index {index!r} has no chunks - run `specbridge ingest` first")


def run_retrieval(ctx: SuiteContext) -> SuiteOutput:
    index = ctx.cfg.index_name or ctx.settings.default_index
    _check_index(index)
    emb = ctx.embedder or get_embedder()
    emb.embed_query("warm up")
    rc = ctx.cfg.retrieval
    items = [
        q
        for q in load_qa(split=ctx.split)
        if q.type not in ("unanswerable",) and q.expected_sources
    ]
    results, lat = [], []
    with session_scope() as db:
        for q in items:
            r = retrieve(
                db,
                q.question,
                index=index,
                mode=rc.get("mode"),
                top_k=10,
                rerank=rc.get("rerank"),
                include_superseded=rc.get("include_superseded", False),
                embedder=emb,
            )
            got = [(c.doc_key, c.page_no) for c in r.chunks]
            m = M.retrieval_item_metrics(q, got)
            lat.append(r.latency_ms)
            results.append(
                {
                    "id": q.id,
                    "type": q.type,
                    "question": q.question,
                    "metrics": m,
                    "retrieved": [{"doc_key": d, "page": p} for d, p in got[:10]],
                    "latency_ms": r.latency_ms,
                }
            )
            log.debug("eval.item", suite="retrieval", id=q.id, hit=m["recall"]["@5"])
    agg = M.aggregate_retrieval(results)
    return SuiteOutput(
        results, {"retrieval": agg}, {"retrieval_latency_ms": M.latency_summary(lat)}
    )


def _stale(q: QAItem, answer: str) -> bool:
    if q.type != "revision" or q.superseded_value is None:
        return False
    sv = q.superseded_value
    if isinstance(sv, int | float):
        return M.match_numeric(answer, float(sv), q.unit, q.tolerance or 0.01)
    return M._contains(answer, str(sv))


def run_qa(ctx: SuiteContext) -> SuiteOutput:
    index = ctx.cfg.index_name or ctx.settings.default_index
    _check_index(index)
    assert ctx.llm is not None
    emb = ctx.embedder or get_embedder()
    emb.embed_query("warm up")
    rc, qc = ctx.cfg.retrieval, ctx.cfg.qa
    items = load_qa(split=ctx.split)
    results: list[dict[str, Any]] = []
    ret_lat, llm_lat, total_lat = [], [], []
    aborted = False
    cost0 = ctx.llm.session_cost
    n_before = len(ctx.llm.session_calls)
    with session_scope() as db:
        for q in items:
            if ctx.llm.session_cost - cost0 > ctx.max_cost:
                aborted = True
                log.error("eval.aborted", reason="cost limit", limit=ctx.max_cost)
                break
            calls0 = len(ctx.llm.session_calls)
            res = answer_question(
                db,
                q.question,
                ctx.llm,
                index=index,
                top_k=qc.get("top_k") or rc.get("top_k"),
                mode=rc.get("mode"),
                rerank=rc.get("rerank"),
                min_score=qc.get("min_score"),
                embedder=emb,
                write_log=False,
            )
            exp = {s.doc_key: set(s.pages) for s in q.expected_sources}
            on_exp = sum(
                1
                for c in res.citations
                if c["doc_key"] in exp and (not exp[c["doc_key"]] or c["page"] in exp[c["doc_key"]])
            )
            correct = M.answer_correct(q, res.answer, res.abstained)
            judge_score: int | None = None
            if q.match == "judge":
                judge_score = (
                    1
                    if res.abstained
                    else judge_answer(ctx.llm, q.question, str(q.expected_answer), res.answer)
                )
            calls = ctx.llm.session_calls[calls0:]
            real = [c for c in calls if not c["cache_hit"] and c["purpose"] == "qa"]
            llm_ms = sum(c["latency_ms"] for c in real)
            ret_ms = res.retrieval.latency_ms if res.retrieval else 0
            if real and len(real) == len([c for c in calls if c["purpose"] == "qa"]):
                llm_lat.append(llm_ms)
                total_lat.append(res.latency_ms)
            ret_lat.append(ret_ms)
            results.append(
                {
                    "id": q.id,
                    "type": q.type,
                    "question": q.question,
                    "answer": res.answer,
                    "abstained": res.abstained,
                    "abstain_reason": res.abstain_reason,
                    "expect_abstain": q.expect_abstain,
                    "correct": correct,
                    "injection_followed": M.injection_followed(q, res.answer)
                    if q.forbidden
                    else False,
                    "citations_total": len(res.citations),
                    "citations_on_expected": on_exp,
                    "dropped_citations": res.dropped_citations,
                    "stale": _stale(q, res.answer),
                    "judge_score": judge_score,
                    "latency_ms": res.latency_ms,
                    "retrieval_ms": ret_ms,
                    "llm_ms": llm_ms,
                    "cost_usd": res.cost_usd,
                    "cache_hit": any(c["cache_hit"] for c in calls),
                }
            )
    cost = ctx.llm.session_cost - cost0
    n = len(results)
    calls = ctx.llm.session_calls[n_before:]
    ops = {
        "retrieval_latency_ms": M.latency_summary(ret_lat),
        "llm_latency_ms": M.latency_summary(llm_lat),
        "total_latency_ms": M.latency_summary(total_lat),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "cache_hits": sum(c["cache_hit"] for c in calls),
        "llm_calls": len(calls),
        "cost_usd": cost,
        "cost_per_100_queries": (cost / n * 100) if n else None,
    }
    notes = []
    if ctx.provider_name == "fake":
        notes.append(
            "fake provider: extractive responder and constant judge - pipeline check only, "
            "NOT a quality benchmark"
        )
    notes.append("judge scores are uncalibrated (judge_calibration.jsonl not scored by a human)")
    return SuiteOutput(
        results,
        {"qa": M.aggregate_qa(results)},
        ops,
        cost,
        {"answer": ctx.llm.settings.model_for("qa"), "judge": ctx.llm.settings.model_for("judge")},
        sorted({c["prompt_version"] for c in calls if c["prompt_version"]}),
        notes,
        aborted,
    )


SUITE_RUNNERS: dict[str, Callable[[SuiteContext], SuiteOutput]] = {
    "retrieval": run_retrieval,
    "qa": run_qa,
}


def register_suite(name: str, fn: Callable[[SuiteContext], SuiteOutput]) -> None:
    SUITE_RUNNERS[name] = fn


def suite_item_count(suite: str, split: str) -> int:
    if suite in ("retrieval", "qa"):
        return len(load_qa(split=split))
    if suite == "extraction":
        from specbridge.eval.datasets import DATASET_DIR, read_jsonl

        recs = read_jsonl(DATASET_DIR / "extraction_synthetic.jsonl") + read_jsonl(
            DATASET_DIR / "extraction_real.jsonl"
        )
        return sum(1 for r in recs if split in ("all", r["split"]))
    return 0


# ------------------------------------------------------------------- driver
def run_eval(
    suites: list[str],
    split: str,
    cfg: RunConfig,
    tag: str,
    *,
    use_cache: bool = False,
    provider: str | None = None,
    dry_run: bool = False,
    out_dir: Path = RESULTS_DIR,
) -> dict[str, Any]:
    from specbridge.eval import suites_extra  # noqa: F401  (registers extraction/agent suites)

    settings = get_settings()
    provider_name = (provider or settings.llm_provider).lower()
    ctx = SuiteContext(
        settings, cfg, split, use_cache, provider_name, max_cost=settings.eval_max_cost_usd
    )
    est = sum(estimate_cost(s, suite_item_count(s, split) or 40, ctx) for s in suites)
    print(
        f"estimated cost: ${est:.4f} (limit ${settings.eval_max_cost_usd:.2f}, provider={provider_name})"
    )
    if est > settings.eval_max_cost_usd:
        raise EvalBudgetError(
            f"estimated cost ${est:.2f} exceeds EVAL_MAX_COST_USD ${settings.eval_max_cost_usd:.2f}"
        )
    if dry_run:
        return {"estimated_cost_usd": est}
    if provider_name != "fake":
        key_ok = settings.anthropic_api_key if provider_name == "anthropic" else True
        if not key_ok:
            raise RuntimeError("ANTHROPIC_API_KEY is not set: paid runs are blocked")
    ctx.llm, _ = make_llm(settings, provider_name, use_cache)
    created = datetime.now()
    sha = git_sha()
    run_id = f"{created:%Y%m%d-%H%M%S}_{sha}_{tag}"
    log.info("eval.run_started", run_id=run_id, suites=suites, split=split, provider=provider_name)
    t0 = time.perf_counter()
    result: dict[str, Any] = {
        "run_id": run_id,
        "created_at": created.isoformat(timespec="seconds"),
        "git_sha": sha,
        "tag": tag,
        "suites": suites,
        "split": split,
        "provider": provider_name,
        "config": cfg.model_dump(),
        "estimated_cost_usd": est,
        "datasets": dataset_hashes(),
        "models": {},
        "prompt_versions": [],
        "items": {},
        "aggregates": {},
        "ops": {},
        "notes": [],
        "cost_usd": 0.0,
        "aborted": False,
        "embedding_model": settings.embedding_model,
    }
    for s in suites:
        if s not in SUITE_RUNNERS:
            raise ValueError(f"unknown suite {s!r}")
        out = SUITE_RUNNERS[s](ctx)
        result["items"][s] = out.items
        result["aggregates"].update(out.aggregates)
        result["ops"][s] = out.ops
        result["models"].update(out.models)
        result["prompt_versions"] = sorted(
            set(result["prompt_versions"]) | set(out.prompt_versions)
        )
        result["notes"].extend(out.notes)
        result["cost_usd"] += out.cost_usd
        result["aborted"] = result["aborted"] or out.aborted
    result["duration_s"] = round(time.perf_counter() - t0, 2)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.json").write_text(json.dumps(result, indent=1, default=str))
    (out_dir / f"{run_id}.md").write_text(render_markdown(result))
    log.info(
        "eval.run_finished", run_id=run_id, cost_usd=result["cost_usd"], aborted=result["aborted"]
    )
    return result


# ---------------------------------------------------------------- rendering
def fmt_metric(m: dict[str, Any] | None) -> str:
    if not m or m.get("value") is None:
        return "n/a"
    v = m["value"]
    s = f"{v:.3f}"
    if "ci" in m:
        s += f" [{m['ci'][0]:.3f}, {m['ci'][1]:.3f}]"
    return s + f" (n={m.get('n')})"


def render_markdown(r: dict[str, Any]) -> str:
    L = [
        f"# Eval run `{r['run_id']}`",
        "",
        f"- suites: {', '.join(r['suites'])} · split: **{r['split']}** · provider: {r['provider']}",
        f"- git: `{r['git_sha']}` · created {r['created_at']} · duration {r.get('duration_s')} s · "
        f"cost ${r['cost_usd']:.4f}",
        f"- embedding model: {r.get('embedding_model')} · models: {r['models'] or 'n/a'}",
        f"- prompt versions: {', '.join(r['prompt_versions']) or 'n/a'}",
        f"- config: `{json.dumps(r['config'])}`",
    ]
    if r.get("aborted"):
        L.append("- **ABORTED**: cost limit reached; results are partial")
    for n in r.get("notes", []):
        L.append(f"- note: {n}")
    agg = r["aggregates"]
    if "retrieval" in agg:
        o = agg["retrieval"]["overall"]
        L += ["", "## Retrieval", "", "| metric | value [95% CI] |", "|---|---|"]
        for k in ("recall_at_1", "recall_at_3", "recall_at_5", "recall_at_10"):
            L.append(f"| {k} | {fmt_metric(o[k])} |")
        L.append(f"| mrr | {fmt_metric(o['mrr'])} |")
        L += ["", "| type | n | recall@5 | mrr |", "|---|---|---|---|"]
        for t, v in agg["retrieval"]["by_type"].items():
            L.append(
                f"| {t} | {v['n']} | {fmt_metric(v['recall_at_5'])} | {v['mrr']['value']:.3f} |"
            )
    if "qa" in agg:
        q = agg["qa"]
        L += ["", "## QA", "", "| metric | value [95% CI] |", "|---|---|"]
        for k in (
            "accuracy",
            "abstention_precision",
            "abstention_recall",
            "over_abstention_rate",
            "injection_resistance",
            "citation_precision",
            "citation_coverage",
            "revision_stale_rate",
        ):
            L.append(f"| {k} | {fmt_metric(q[k])} |")
        j = q["judge_usefulness"]
        L.append(f"| judge_usefulness (1-3, uncalibrated) | {j['value']} (n={j['n']}) |")
        L += ["", "| type | accuracy |", "|---|---|"]
        for t, v in q["accuracy_by_type"].items():
            L.append(f"| {t} | {fmt_metric(v)} |")
    for key in ("extraction", "extraction_real"):
        if key in agg:
            L += _render_extraction(key, agg[key])
    for k, v in agg.items():
        if k not in ("retrieval", "qa", "extraction", "extraction_real"):
            L += ["", f"## {k}", "", "```json", json.dumps(v, indent=1, default=str)[:6000], "```"]
    L += ["", "## Ops", "", "```json", json.dumps(r["ops"], indent=1, default=str), "```", ""]
    return "\n".join(L)


def _render_extraction(key: str, e: dict[str, Any]) -> list[str]:
    title = "Extraction (PROVISIONAL labels)" if key.endswith("real") else "Extraction"
    L = [
        "",
        f"## {title}",
        "",
        f"documents: {e['n_documents']}",
        "",
        "| metric | value [95% CI] |",
        "|---|---|",
        f"| micro precision | {fmt_metric(e['micro']['precision'])} |",
        f"| micro recall | {fmt_metric(e['micro']['recall'])} |",
        f"| micro F1 | {e['micro_f1']['value']:.3f} |",
        f"| evidence validity | {fmt_metric(e['evidence_validity'])} |",
        f"| auto-validated | {fmt_metric(e['auto_validated_rate'])} |",
        f"| needs review | {fmt_metric(e['needs_review_rate'])} |",
        f"| precision of validated docs (all fields right) | {fmt_metric(e['validated_doc_precision'])} |",
        f"| precision of validated fields | {fmt_metric(e['validated_field_precision'])} |",
        f"| mean attempts | {e['attempts_mean']['value']:.2f} |",
        "",
        "| field | precision | recall | F1 |",
        "|---|---|---|---|",
    ]
    for f, v in e["per_field"].items():
        pv, rv = v["precision"]["value"], v["recall"]["value"]
        L.append(
            f"| {f} | {'n/a' if pv is None else f'{pv:.3f}'} (n={v['precision']['n']}) | "
            f"{'n/a' if rv is None else f'{rv:.3f}'} (n={v['recall']['n']}) | "
            f"{v['f1']['value']:.3f} |"
        )
    return L


def latest_run(out_dir: Path = RESULTS_DIR, tag: str | None = None) -> Path:
    files = sorted(
        p
        for p in out_dir.glob("*.json")
        if p.name != "baseline.json" and (tag is None or p.stem.endswith(f"_{tag}"))
    )
    if not files:
        raise FileNotFoundError(f"no eval results in {out_dir}")
    return files[-1]
