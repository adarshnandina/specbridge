"""LLM extraction -> normalise -> validate -> (one retry with errors) -> persisted Extraction."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from specbridge import metrics
from specbridge.db.models import Chunk, Document, Extraction, Page
from specbridge.errors import NotFoundError
from specbridge.extraction.normalize import Normalized, normalize_spec
from specbridge.extraction.schema import SCHEMA_VERSION, ComponentSpec, ValidationIssue
from specbridge.extraction.validators import errors, validate
from specbridge.llm.usage import LLMService
from specbridge.logging_setup import get_logger
from specbridge.prompts import load_prompt

log = get_logger("specbridge.extraction")
PROMPT_NAME, PROMPT_VERSION = "extraction", 1
MAX_CHARS = 36_000  # ~9k tokens of page text per request
SPEC_KEYWORDS = re.compile(
    r"voltage|current|temperature|protection|weight|dimension|power|interface|approval|ip\s?\d",
    re.I,
)


@dataclass
class ExtractionOutcome:
    normalized: Normalized
    issues: list[ValidationIssue]
    attempts: int
    model: str
    prompt_label: str
    raw: dict[str, Any]


def select_pages(
    pages: dict[int, str], table_pages: set[int], max_chars: int = MAX_CHARS
) -> dict[int, str]:
    """Pages with tables or spec keywords (page 1 always for identity), within the char budget."""
    if not pages:
        return {}

    def score(n: int, t: str) -> int:
        return (3 if n in table_pages else 0) + min(5, len(SPEC_KEYWORDS.findall(t)))

    order = [1] if 1 in pages else []
    order += sorted((n for n in pages if n != 1), key=lambda n: (-score(n, pages[n]), n))
    chosen: dict[int, str] = {}
    used = 0
    for n in order:
        text = pages[n]
        if used + len(text) > max_chars:
            if chosen:
                continue
            text = text[:max_chars]
        chosen[n] = text
        used += len(text)
    return dict(sorted(chosen.items()))


def build_message(
    pages: dict[int, str],
    errors_prev: list[ValidationIssue] | None = None,
    prev_output: dict[str, Any] | None = None,
) -> str:
    body = "\n".join(
        f'<page number="{n}">\n{t.replace("</page", "&lt;/page")}\n</page>'
        for n, t in pages.items()
    )
    msg = f"<datasheet>\n{body}\n</datasheet>\n\nExtract the component specification."
    if errors_prev:
        msg += (
            "\n\nYour previous extraction failed validation:\n"
            + "\n".join(f"- {i.field}: {i.message}" for i in errors_prev)
            + "\nPrevious output:\n"
            + json.dumps(prev_output, default=str)[:4000]
            + "\nCorrect ONLY what the datasheet supports; set a field to null if it cannot be "
            "supported with a verbatim quote. Resubmit."
        )
    return msg


def load_document_pages(db: Session, doc: Document) -> tuple[dict[int, str], set[int]]:
    rows = db.execute(
        select(Page.page_no, Page.text).where(Page.document_id == doc.id).order_by(Page.page_no)
    ).all()
    pages = {int(n): str(t) for n, t in rows}
    tables = {
        int(p)
        for (p,) in db.execute(
            select(Chunk.page_no).where(Chunk.document_id == doc.id, Chunk.chunk_type == "table")
        ).all()
    }
    return pages, tables


def run_extraction(
    llm: LLMService,
    pages: dict[int, str],
    table_pages: set[int],
    *,
    retry: bool = True,
    model: str | None = None,
) -> ExtractionOutcome:
    prompt = load_prompt(PROMPT_NAME, PROMPT_VERSION)
    chosen = select_pages(pages, table_pages)
    if model:
        llm.settings = llm.settings.model_copy(
            update={"model_extraction": model, "bedrock_model_extraction": model}
        )
    attempts = 1
    spec = _call(llm, prompt.text, build_message(chosen), prompt.label, model)
    norm = normalize_spec(spec)
    issues = norm.issues + validate(norm.data, norm.evidence, pages)
    raw = spec.model_dump()
    if retry and errors(issues):
        log.info("extraction.retry", errors=len(errors(issues)))
        attempts = 2
        spec2 = _call(
            llm, prompt.text, build_message(chosen, errors(issues), raw), prompt.label, model
        )
        norm2 = normalize_spec(spec2)
        issues2 = norm2.issues + validate(norm2.data, norm2.evidence, pages)
        norm, issues, raw = norm2, issues2, spec2.model_dump()
    return ExtractionOutcome(
        norm, issues, attempts, llm.settings.model_for("extraction"), prompt.label, raw
    )


def _call(llm: LLMService, system: str, user: str, label: str, model: str | None) -> ComponentSpec:
    return llm.structured(
        ComponentSpec,
        tool_name="submit_spec",
        tool_description="Submit the extracted component specification.",
        system=system,
        messages=[{"role": "user", "content": user}],
        purpose="extraction",
        prompt_version=label,
        max_tokens=2500,
    )


def extract_document(
    db: Session,
    llm: LLMService,
    document_id: uuid.UUID,
    *,
    retry: bool = True,
    model: str | None = None,
) -> Extraction:
    doc = db.get(Document, document_id)
    if doc is None or doc.status != "ingested":
        raise NotFoundError("Document not found")
    pages, table_pages = load_document_pages(db, doc)
    out = run_extraction(llm, pages, table_pages, retry=retry, model=model)
    errs = errors(out.issues)
    status = "pending_review" if errs else "validated"
    ex = Extraction(
        document_id=doc.id,
        schema_version=SCHEMA_VERSION,
        model=out.model,
        prompt_version=out.prompt_label,
        status=status,
        data=out.normalized.data,
        evidence=out.normalized.evidence,
        validation_errors=[i.model_dump() for i in out.issues],
        attempts=out.attempts,
    )
    db.add(ex)
    db.flush()
    metrics.EXTRACTION_STATUS.labels(status).inc()
    log.info(
        "extraction.done",
        extraction_id=str(ex.id),
        document=doc.doc_key,
        status=status,
        attempts=out.attempts,
        errors=len(errs),
    )
    if errs:
        log.warning(
            "extraction.validation_failed",
            extraction_id=str(ex.id),
            errors=[f"{i.field}:{i.rule}" for i in errs][:10],
        )
    return ex
