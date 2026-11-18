from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from specbridge.api.deps import get_db, require
from specbridge.auth.api_keys import Principal
from specbridge.llm.usage import LLMService, build_provider
from specbridge.qa.service import answer_question

router = APIRouter(tags=["query"])

_llm: LLMService | None = None


def get_llm() -> LLMService:
    """One LLMService per process (provider chosen from settings)."""
    global _llm
    if _llm is None:
        provider = build_provider()
        if provider.name == "fake":
            from specbridge.llm.fake_handlers import register_default_handlers
            from specbridge.llm.fake_provider import FakeProvider

            assert isinstance(provider, FakeProvider)
            register_default_handlers(provider)
        _llm = LLMService(provider)
    return _llm


def set_llm(llm: LLMService | None) -> None:
    global _llm
    _llm = llm


class QueryIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    index_name: str | None = Field(default=None, max_length=64)
    top_k: int | None = Field(default=None, ge=1, le=30)
    mode: Literal["vector", "keyword", "hybrid"] | None = None
    rerank: bool | None = None


class CitationOut(BaseModel):
    source_id: str
    doc_key: str
    page: int
    quote: str
    chunk_id: str
    document_id: str
    image_url: str


class QueryOut(BaseModel):
    answer: str
    citations: list[CitationOut]
    abstained: bool
    abstain_reason: str | None
    latency_ms: int
    cost_usd: float
    request_id: str | None


@router.post("/query", response_model=QueryOut)
def query(
    body: QueryIn,
    db: Session = Depends(get_db),
    llm: LLMService = Depends(get_llm),
    p: Principal = Depends(require("query")),
) -> dict[str, Any]:
    res = answer_question(
        db,
        body.question,
        llm,
        index=body.index_name,
        top_k=body.top_k,
        mode=body.mode,
        rerank=body.rerank,
        actor=p.user,
    )
    return res.to_dict()
