from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PartUpsert(BaseModel):
    spec: dict[str, Any]
    lifecycle_status: str | None = Field(default=None, pattern="^(active|nrnd|discontinued)$")


class ChangeRequestIn(BaseModel):
    original_part: str
    proposed_part: str
    rationale: str = ""
    evidence: list[Any] = Field(default_factory=list)
    requested_by: str = ""
    approved_by: str | None = None


class Faults(BaseModel):
    failure_rate: float = Field(0.0, ge=0, le=1)
    fail_first_n: int = Field(0, ge=0)
    latency_ms: int = Field(0, ge=0)
