"""Retrieval service: vector | keyword | hybrid (RRF), optional rerank. Configurable per call."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from specbridge import metrics
from specbridge.config import get_settings
from specbridge.db.models import Chunk, Document
from specbridge.ingestion.embeddings import Embedder, get_embedder
from specbridge.logging_setup import get_logger
from specbridge.retrieval.hybrid import rrf
from specbridge.retrieval.keyword import keyword_search
from specbridge.retrieval.rerank import Reranker, get_reranker
from specbridge.retrieval.vector import similarities, vector_search

log = get_logger("specbridge.retrieval")
CANDIDATES = 30
RERANK_POOL = 20


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    doc_key: str
    page_no: int
    bboxes: list[Any]
    content: str
    scores: dict[str, float] = field(default_factory=dict)
    chunk_type: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    mode: str
    latency_ms: int
    top_vector_score: float = 0.0
    timings_ms: dict[str, int] = field(default_factory=dict)


def _rerank_text(chunk: Chunk) -> str:
    header = (chunk.meta or {}).get("context_header")
    return f"{header}\n{chunk.content}" if header else chunk.content


def retrieve(
    db: Session,
    query: str,
    *,
    index: str | None = None,
    mode: str | None = None,
    top_k: int | None = None,
    rerank: bool | None = None,
    include_superseded: bool = False,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
) -> RetrievalResult:
    s = get_settings()
    index = index or s.default_index
    mode = mode or s.retrieval_mode
    top_k = top_k or s.retrieval_top_k
    rerank = s.rerank_enabled if rerank is None else rerank
    if mode not in ("vector", "keyword", "hybrid"):
        raise ValueError(f"unknown retrieval mode {mode!r}")
    t0 = time.perf_counter()
    timings: dict[str, int] = {}
    vec_hits: list[tuple[uuid.UUID, float]] = []
    kw_hits: list[tuple[uuid.UUID, float]] = []
    # The query embedding is always computed: the vector similarity is the abstention signal.
    t = time.perf_counter()
    qvec = (embedder or get_embedder()).embed_query(query)
    timings["embed"] = int((time.perf_counter() - t) * 1000)
    if mode in ("vector", "hybrid"):
        t = time.perf_counter()
        vec_hits = vector_search(
            db, qvec, index=index, limit=CANDIDATES, include_superseded=include_superseded
        )
        timings["vector"] = int((time.perf_counter() - t) * 1000)
    if mode in ("keyword", "hybrid"):
        t = time.perf_counter()
        kw_hits = keyword_search(
            db, query, index=index, limit=CANDIDATES, include_superseded=include_superseded
        )
        timings["keyword"] = int((time.perf_counter() - t) * 1000)

    vscore = dict(vec_hits)
    kscore = dict(kw_hits)
    fused: dict[uuid.UUID, float] = {}
    if mode == "vector":
        order = [i for i, _ in vec_hits]
        fused = {i: sc for i, sc in vec_hits}
    elif mode == "keyword":
        order = [i for i, _ in kw_hits]
        fused = {i: sc for i, sc in kw_hits}
    else:
        f = rrf([[i for i, _ in vec_hits], [i for i, _ in kw_hits]])
        order = [i for i, _ in f]
        fused = dict(f)
    pool = order[: (RERANK_POOL if rerank else top_k)]

    rerank_scores: dict[uuid.UUID, float] = {}
    chosen = pool[:top_k]
    rows: dict[uuid.UUID, tuple[Chunk, Document]] = {}
    if pool:
        stmt = (
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.id.in_(pool))
        )
        rows = {c.id: (c, d) for c, d in db.execute(stmt)}
    if rerank and pool:
        t = time.perf_counter()
        rr = reranker or get_reranker()
        # The reranker must see what the embedder saw: context header + content (a table chunk
        # alone does not say which part it describes).
        scores = rr.score(query, [_rerank_text(rows[i][0]) for i in pool if i in rows])
        rerank_scores = dict(zip([i for i in pool if i in rows], scores, strict=True))
        chosen = sorted(rerank_scores, key=lambda i: -rerank_scores[i])[:top_k]
        timings["rerank"] = int((time.perf_counter() - t) * 1000)
    missing = [i for i in chosen if i not in vscore]
    vscore.update(similarities(db, qvec, missing))

    out = []
    for i in chosen:
        if i not in rows:
            continue
        c, d = rows[i]
        sc = {
            "vector": vscore.get(i, 0.0),
            "keyword": kscore.get(i, 0.0),
            "fused": fused.get(i, 0.0),
        }
        if i in rerank_scores:
            sc["rerank"] = rerank_scores[i]
        out.append(
            RetrievedChunk(
                str(c.id),
                str(d.id),
                d.doc_key,
                c.page_no,
                c.bboxes,
                c.content,
                sc,
                c.chunk_type,
                c.meta,
            )
        )
    latency = int((time.perf_counter() - t0) * 1000)
    metrics.RETRIEVAL_LATENCY.labels(mode).observe(latency / 1000)
    top_v = max((c.scores["vector"] for c in out), default=0.0)
    log.info(
        "retrieval.done",
        mode=mode,
        index=index,
        top_k=top_k,
        rerank=rerank,
        results=len(out),
        latency_ms=latency,
        top_vector_score=round(top_v, 4),
    )
    return RetrievalResult(out, mode, latency, top_v, timings)
