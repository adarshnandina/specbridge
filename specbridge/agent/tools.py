"""Agent tools. Read tools are deterministic; the write tool is guarded by an approved approval row.

The LLM never writes SQL: search_parts builds a parameterised SQLAlchemy query from validated,
whitelisted constraint fields.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Float, cast, select
from sqlalchemy.orm import Session

from specbridge.agent.models import Constraint
from specbridge.db.models import Approval, Document, Extraction
from specbridge.erp_client.client import ErpClient
from specbridge.extraction import units as U
from specbridge.extraction.fields import ip_at_least, ranges_overlap
from specbridge.ingestion.embeddings import Embedder
from specbridge.retrieval.service import retrieve

CANDIDATE_STATUSES = ("validated", "approved", "pushed")
MAX_CANDIDATES = 10
LIST_FIELDS = {"certifications", "interfaces"}


class WriteNotApproved(Exception):
    pass


def check_constraint(spec: dict[str, Any], c: Constraint) -> bool:
    actual = spec.get(c.field)
    if actual is None:
        return False
    v: Any = c.value
    if c.field == "ip_rating" and c.op in ("gte", "eq"):
        return (
            ip_at_least(str(actual), str(v))
            if c.op == "gte"
            else str(actual).upper() == str(v).upper().replace(" ", "")
        )
    if isinstance(actual, list):
        items = {str(x).lower() for x in actual}
        norm = {
            str(x).lower()
            for x in (
                U.canonical_interfaces([str(v)])
                if c.field == "interfaces"
                else U.canonical_certs([str(v)])
            )
        }
        if c.op in ("contains", "eq"):
            return bool(norm & items)
        return False
    if c.op in ("gte", "lte"):
        try:
            a, b = float(actual), float(v)
        except (TypeError, ValueError):
            return False
        return a >= b if c.op == "gte" else a <= b
    if c.op == "eq":
        return str(actual).lower() == str(v).lower()
    if c.op == "contains":
        return str(v).lower() in str(actual).lower()
    return False


class AgentTools:
    def __init__(self, db: Session, erp: ErpClient, embedder: Embedder | None = None) -> None:
        self.db, self.erp, self.embedder = db, erp, embedder

    # ------------------------------------------------------------------ reads
    def get_part(self, part_number: str) -> dict[str, Any] | None:
        part = self.erp.get_part(part_number)
        if part is None:
            return None
        ex = self._latest_extraction(part_number)
        return {
            "part_number": part_number,
            "lifecycle_status": part["lifecycle_status"],
            "category": part.get("category"),
            "spec": part["spec"],
            "extraction_id": str(ex.id) if ex else None,
        }

    def _latest_extraction(self, part_number: str) -> Extraction | None:
        stmt = (
            select(Extraction)
            .join(Document, Document.id == Extraction.document_id)
            .where(
                Extraction.data["part_number"].astext == part_number,
                Extraction.status.in_(CANDIDATE_STATUSES),
                Document.is_latest.is_(True),
            )
            .order_by(Extraction.created_at.desc())
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def search_parts(
        self, original: dict[str, Any], constraints: list[Constraint], exclude: str
    ) -> list[dict[str, Any]]:
        spec = original["spec"]
        d = Extraction.data
        stmt = (
            select(Extraction)
            .join(Document, Document.id == Extraction.document_id)
            .where(
                Extraction.status.in_(CANDIDATE_STATUSES),
                Document.is_latest.is_(True),
                d["category"].astext == str(spec.get("category")),
                d["part_number"].astext != exclude,
            )
        )
        if spec.get("operating_temp_min_c") is not None:
            stmt = stmt.where(
                cast(d["operating_temp_min_c"].astext, Float)
                <= float(spec["operating_temp_min_c"]),
                cast(d["operating_temp_max_c"].astext, Float)
                >= float(spec["operating_temp_max_c"]),
            )
        stmt = stmt.order_by(d["part_number"].astext, Extraction.created_at.desc())
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for ex in self.db.scalars(stmt):
            pn = ex.data.get("part_number")
            if not pn or pn in seen:
                continue
            seen.add(pn)
            cand = ex.data
            if not ranges_overlap(
                spec.get("supply_voltage_min_v"),
                spec.get("supply_voltage_max_v"),
                cand.get("supply_voltage_min_v"),
                cand.get("supply_voltage_max_v"),
            ):
                continue
            if not ip_at_least(cand.get("ip_rating"), spec.get("ip_rating")):
                continue
            if not all(check_constraint(cand, c) for c in constraints):
                continue
            erp_part = self.erp.get_part(pn)
            if erp_part is None or erp_part["lifecycle_status"] == "discontinued":
                continue  # never propose a discontinued (or unknown) part
            out.append(
                {
                    "part_number": pn,
                    "extraction_id": str(ex.id),
                    "document_id": str(ex.document_id),
                    "lifecycle_status": erp_part["lifecycle_status"],
                    "spec": cand,
                }
            )
            if len(out) >= MAX_CANDIDATES:
                break
        return out

    def retrieve_evidence(
        self, part_number: str, query: str, limit: int = 3
    ) -> list[dict[str, Any]]:
        res = retrieve(
            self.db, f"{part_number} {query}", top_k=30, mode="hybrid", embedder=self.embedder
        )
        out = []
        for c in res.chunks:
            if part_number in c.doc_key:
                out.append(
                    {
                        "chunk_id": c.chunk_id,
                        "doc_key": c.doc_key,
                        "page": c.page_no,
                        "content": c.content,
                    }
                )
            if len(out) >= limit:
                break
        return out

    # ------------------------------------------------------------------ write
    def create_change_request(self, run_id: uuid.UUID, body: dict[str, Any]) -> dict[str, Any]:
        """The ONLY write tool. Refuses to run unless an approval for this run is approved."""
        approved = self.db.scalar(
            select(Approval.id).where(Approval.run_id == run_id, Approval.status == "approved")
        )
        if approved is None:
            raise WriteNotApproved(f"no approved approval row for run {run_id}")
        return self.erp.create_change_request(body, key=str(run_id))
