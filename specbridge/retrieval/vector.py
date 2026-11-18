"""pgvector cosine-similarity search."""

from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from specbridge.db.models import Chunk, Document


def vector_search(
    db: Session, qvec: list[float], *, index: str, limit: int, include_superseded: bool = False
) -> list[tuple[uuid.UUID, float]]:
    """Returns (chunk_id, cosine_similarity) best-first."""
    db.execute(text("SET LOCAL hnsw.ef_search = 200"))
    dist = Chunk.embedding.cosine_distance(qvec).label("dist")
    stmt = (
        select(Chunk.id, dist)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.index_name == index)
    )
    if not include_superseded:
        stmt = stmt.where(Document.is_latest.is_(True))
    # Deterministic tie-break (random UUIDs differ per database and made evals irreproducible)
    stmt = stmt.order_by(dist, Document.doc_key, Chunk.chunk_index).limit(limit)
    return [(r[0], 1.0 - float(r[1])) for r in db.execute(stmt)]


def similarities(
    db: Session, qvec: list[float], chunk_ids: list[uuid.UUID]
) -> dict[uuid.UUID, float]:
    if not chunk_ids:
        return {}
    dist = Chunk.embedding.cosine_distance(qvec)
    rows = db.execute(select(Chunk.id, dist).where(Chunk.id.in_(chunk_ids)))
    return {r[0]: 1.0 - float(r[1]) for r in rows}
