from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from specbridge.agent.runner import AgentRunner
from specbridge.api.deps import get_db, get_erp, require
from specbridge.api.routers.query import get_llm
from specbridge.auth.api_keys import Principal
from specbridge.db.models import AgentRun, AgentStep, Approval
from specbridge.erp_client.client import ErpClient
from specbridge.errors import NotFoundError
from specbridge.llm.usage import LLMService

router = APIRouter(tags=["agent"])
RUNNER_OPTIONS: dict[str, Any] = {}  # test/scenario hooks (crash_after, step_timeout_s, ...)


def get_runner(
    db: Session = Depends(get_db),
    llm: LLMService = Depends(get_llm),
    erp: ErpClient = Depends(get_erp),
) -> AgentRunner:
    return AgentRunner(db, llm, erp, **RUNNER_OPTIONS)


class RunIn(BaseModel):
    request: str = Field(min_length=5, max_length=1000)


class RunOut(BaseModel):
    id: uuid.UUID
    requested_by: str
    request_text: str
    state: str
    parsed_request: dict[str, Any] | None
    result: dict[str, Any] | None
    error: str | None
    llm_calls_used: int
    created_at: datetime
    updated_at: datetime
    approval_id: uuid.UUID | None = None
    approval_status: str | None = None


class StepOut(BaseModel):
    step_no: int
    state: str
    tool_name: str | None
    tool_input: Any
    tool_output: Any
    status: str
    attempt: int
    latency_ms: int
    error: str | None

    model_config = {"from_attributes": True}


class ApprovalOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    change_request: dict[str, Any]
    status: str
    requested_by: str
    decided_by: str | None
    decided_at: datetime | None
    comment: str | None

    model_config = {"from_attributes": True}


class DecisionIn(BaseModel):
    comment: str = Field(default="", max_length=500)


def run_out(db: Session, run: AgentRun) -> RunOut:
    appr = db.scalar(select(Approval).where(Approval.run_id == run.id))
    out = RunOut.model_validate(
        {
            **{
                c: getattr(run, c)
                for c in (
                    "id",
                    "requested_by",
                    "request_text",
                    "state",
                    "parsed_request",
                    "result",
                    "error",
                    "llm_calls_used",
                    "created_at",
                    "updated_at",
                )
            },
            "approval_id": appr.id if appr else None,
            "approval_status": appr.status if appr else None,
        }
    )
    return out


def get_run_or_404(db: Session, run_id: uuid.UUID) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise NotFoundError("Agent run not found")
    return run


@router.post("/agent/runs", response_model=RunOut, status_code=201)
def start_run(
    body: RunIn,
    db: Session = Depends(get_db),
    runner: AgentRunner = Depends(get_runner),
    p: Principal = Depends(require("write")),
) -> RunOut:
    run = runner.start(p, body.request)
    return run_out(db, run)


@router.get("/agent/runs", response_model=list[RunOut])
def list_runs(
    db: Session = Depends(get_db), _: Principal = Depends(require("read"))
) -> list[RunOut]:
    runs = db.scalars(select(AgentRun).order_by(AgentRun.created_at.desc()).limit(100))
    return [run_out(db, r) for r in runs]


@router.get("/agent/runs/{run_id}", response_model=RunOut)
def get_run(
    run_id: uuid.UUID, db: Session = Depends(get_db), _: Principal = Depends(require("read"))
) -> RunOut:
    return run_out(db, get_run_or_404(db, run_id))


@router.get("/agent/runs/{run_id}/steps", response_model=list[StepOut])
def get_steps(
    run_id: uuid.UUID, db: Session = Depends(get_db), _: Principal = Depends(require("read"))
) -> list[AgentStep]:
    get_run_or_404(db, run_id)
    return list(
        db.scalars(select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.step_no))
    )


@router.post("/agent/runs/{run_id}/retry", response_model=RunOut)
def retry_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    runner: AgentRunner = Depends(get_runner),
    p: Principal = Depends(require("write")),
) -> RunOut:
    return run_out(db, runner.retry(run_id, p))


@router.get("/approvals", response_model=list[ApprovalOut])
def list_approvals(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: Principal = Depends(require("read")),
) -> list[Approval]:
    stmt = select(Approval).order_by(Approval.created_at.desc())
    if status:
        stmt = stmt.where(Approval.status == status)
    return list(db.scalars(stmt))


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalOut)
def approve(
    approval_id: uuid.UUID,
    body: DecisionIn | None = None,
    runner: AgentRunner = Depends(get_runner),
    p: Principal = Depends(require("approve")),
) -> Approval:
    return runner.decide(approval_id, p, True, body.comment if body else "")


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalOut)
def reject(
    approval_id: uuid.UUID,
    body: DecisionIn | None = None,
    runner: AgentRunner = Depends(get_runner),
    p: Principal = Depends(require("approve")),
) -> Approval:
    return runner.decide(approval_id, p, False, body.comment if body else "")
