"""Q&A with verified citations and abstention (Section 7.5)."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from specbridge.db.models import QueryLog
from specbridge.ingestion.embeddings import Embedder
from specbridge.llm.usage import LLMService
from specbridge.logging_setup import get_logger
from specbridge.prompts import load_prompt
from specbridge.qa.citations import verify_citations
from specbridge.retrieval.service import RetrievalResult, retrieve

log = get_logger("specbridge.qa")
PROMPT_NAME, PROMPT_VERSION = "qa_answer", 1
ABSTAIN_TEXT = "I couldn't find support for this in the documents."


class CitationIn(BaseModel):
    source_id: str
    quote: str


class SubmitAnswer(BaseModel):
    answerable: bool
    answer: str = ""
    citations: list[CitationIn] = Field(default_factory=list)


@dataclass
class AnswerResult:
    question: str
    answer: str
    citations: list[dict[str, Any]]
    abstained: bool
    abstain_reason: str | None
    latency_ms: int
    cost_usd: float
    request_id: str | None
    retrieval: RetrievalResult | None = field(default=None, repr=False)
    dropped_citations: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("retrieval", None)
        return d


def escape_source(text: str) -> str:
    return text.replace("</source", "&lt;/source").replace("<source", "&lt;source")


def build_user_message(question: str, chunks: list[Any]) -> tuple[str, dict[str, Any]]:
    """Wrap sources as untrusted data. Returns (message, {source_id: chunk})."""
    parts, mapping = ["<sources>"], {}
    for i, c in enumerate(chunks, start=1):
        sid = f"S{i}"
        mapping[sid] = c
        parts.append(
            f'<source id="{sid}" doc="{c.doc_key}" page="{c.page_no}">\n'
            f"{escape_source(c.content)}\n</source>"
        )
    parts.append("</sources>")
    parts.append(f"\nQuestion: {question}")
    return "\n".join(parts), mapping


def _request_id() -> str | None:
    from structlog.contextvars import get_contextvars

    v = get_contextvars().get("request_id")
    return str(v) if v else None


def answer_question(
    db: Session,
    question: str,
    llm: LLMService,
    *,
    index: str | None = None,
    top_k: int | None = None,
    mode: str | None = None,
    rerank: bool | None = None,
    min_score: float | None = None,
    actor: str | None = None,
    embedder: Embedder | None = None,
    write_log: bool = True,
) -> AnswerResult:
    from specbridge.config import get_settings

    s = get_settings()
    threshold = s.abstain_min_score if min_score is None else min_score
    t0 = time.perf_counter()
    cost0 = llm.session_cost
    ret = retrieve(
        db, question, index=index, mode=mode, top_k=top_k, rerank=rerank, embedder=embedder
    )
    used_index = index or s.default_index
    abstain_reason: str | None = None
    answer, citations, dropped = ABSTAIN_TEXT, [], 0

    if not ret.chunks or ret.top_vector_score < threshold:
        abstain_reason = "low_retrieval_score"
        log.info("qa.abstained", reason=abstain_reason, top_score=ret.top_vector_score)
    else:
        user_msg, mapping = build_user_message(question, ret.chunks)
        prompt = load_prompt(PROMPT_NAME, PROMPT_VERSION)
        out = llm.structured(
            SubmitAnswer,
            tool_name="submit_answer",
            tool_description="Submit the final answer with verbatim citations.",
            system=prompt.text,
            messages=[{"role": "user", "content": user_msg}],
            purpose="qa",
            prompt_version=prompt.label,
            max_tokens=700,
        )
        verified = verify_citations(
            [(c.source_id, c.quote) for c in out.citations],
            {k: v.content for k, v in mapping.items()},
        )
        for v in verified:
            if not v.valid:
                dropped += 1
                log.warning(
                    "qa.citation_dropped",
                    source_id=v.source_id,
                    reason=v.reason,
                    quote=v.quote[:80],
                )
        good = [v for v in verified if v.valid]
        if not out.answerable:
            abstain_reason = "model_unanswerable"
            answer = out.answer.strip() or ABSTAIN_TEXT
            log.info("qa.abstained", reason=abstain_reason)
        elif not good:
            abstain_reason = "unsupported_answer_blocked"
            log.warning("qa.unsupported_answer_blocked", question=question[:120])
        else:
            answer = out.answer.strip()
            seen: set[tuple[str, str]] = set()
            for v in good:
                c = mapping[v.source_id]
                if (v.source_id, v.quote) in seen:
                    continue
                seen.add((v.source_id, v.quote))
                citations.append(
                    {
                        "source_id": v.source_id,
                        "doc_key": c.doc_key,
                        "page": c.page_no,
                        "quote": v.quote,
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "image_url": f"/documents/{c.document_id}/pages/{c.page_no}/image"
                        f"?chunk_id={c.chunk_id}",
                    }
                )
            log.info("qa.answered", citations=len(citations), dropped=dropped)

    abstained = abstain_reason is not None
    if abstained and abstain_reason == "unsupported_answer_blocked":
        answer = ABSTAIN_TEXT
    latency = int((time.perf_counter() - t0) * 1000)
    cost = llm.session_cost - cost0
    res = AnswerResult(
        question,
        answer,
        citations,
        abstained,
        abstain_reason,
        latency,
        cost,
        _request_id(),
        ret,
        dropped,
    )
    if write_log:
        db.add(
            QueryLog(
                request_id=res.request_id,
                actor=actor,
                question=question,
                index_name=used_index,
                retrieval={
                    "mode": ret.mode,
                    "top_vector_score": ret.top_vector_score,
                    "chunks": [
                        {
                            "chunk_id": c.chunk_id,
                            "doc_key": c.doc_key,
                            "page": c.page_no,
                            "scores": c.scores,
                        }
                        for c in ret.chunks
                    ],
                },
                answer={"answer": answer, "citations": citations, "reason": abstain_reason},
                abstained=abstained,
                latency_ms=latency,
                cost_usd=cost,
            )
        )
        db.flush()
    return res


__all__ = ["answer_question", "AnswerResult", "SubmitAnswer", "ABSTAIN_TEXT"]
