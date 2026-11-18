from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from specbridge.extraction.fields import AGENT_CONSTRAINT_FIELDS

Op = Literal["eq", "gte", "lte", "contains"]
PN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{1,40}$")


class Constraint(BaseModel):
    field: str = Field(json_schema_extra={"enum": list(AGENT_CONSTRAINT_FIELDS)})
    op: Op
    value: str | float | int | bool

    @field_validator("field")
    @classmethod
    def _whitelisted(cls, v: str) -> str:
        if v not in AGENT_CONSTRAINT_FIELDS:
            raise ValueError(f"field {v!r} not allowed; use one of {list(AGENT_CONSTRAINT_FIELDS)}")
        return v


class ParsedRequest(BaseModel):
    part_number: str
    constraints: list[Constraint] = Field(default_factory=list, max_length=8)

    @field_validator("part_number")
    @classmethod
    def _pn(cls, v: str) -> str:
        v = v.strip()
        if not PN_PATTERN.match(v):
            raise ValueError(f"{v!r} does not look like a part number")
        return v


class ClaimCitation(BaseModel):
    chunk_id: str
    quote: str


class Claim(BaseModel):
    text: str
    citations: list[ClaimCitation] = Field(default_factory=list)


class RankedCandidate(BaseModel):
    part_number: str
    claims: list[Claim] = Field(default_factory=list)


class SubmitRanking(BaseModel):
    ranking: list[RankedCandidate] = Field(max_length=3)


class RetrieveEvidenceArgs(BaseModel):
    part_number: str
    query: str = Field(max_length=300)


def as_dict(m: BaseModel) -> dict[str, Any]:
    return m.model_dump()
