"""Postgres full-text 'keyword' search (ts_rank_cd). Not BM25."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from specbridge.db.models import Chunk, Document

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "with",
        "within",
        "would",
        "you",
        "your",
        "list",
        "give",
        "tell",
        "me",
        "please",
        "carry",
        "support",
        "supports",
        "according",
        "latest",
        "datasheet",
        "revision",
    ]
)
TOKEN_RE = re.compile(r"[A-Za-z0-9Ö][A-Za-z0-9Ö\-/.,]*[A-Za-z0-9]|[A-Za-z0-9]")


def build_query(question: str) -> str:
    """OR-combine content words so natural-language questions can match (websearch syntax)."""
    toks: list[str] = []
    for t in TOKEN_RE.findall(question):
        t = t.strip(".,")
        if not t or t.lower() in STOPWORDS:
            continue
        if t not in toks:
            toks.append(t)
    return " or ".join(toks)


def keyword_search(
    db: Session, question: str, *, index: str, limit: int, include_superseded: bool = False
) -> list[tuple[uuid.UUID, float]]:
    q = build_query(question)
    if not q:
        return []
    tsq = func.websearch_to_tsquery("simple", q)
    rank = func.ts_rank_cd(Chunk.content_tsv, tsq).label("rank")
    stmt = (
        select(Chunk.id, rank)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.index_name == index, Chunk.content_tsv.op("@@")(tsq))
    )
    if not include_superseded:
        stmt = stmt.where(Document.is_latest.is_(True))
    stmt = stmt.order_by(rank.desc(), Chunk.id).limit(limit)
    return [(r[0], float(r[1])) for r in db.execute(stmt)]
