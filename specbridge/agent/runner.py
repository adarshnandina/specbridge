"""Part-substitution agent: explicit, persisted state machine (Section 7.8).

Guarantees enforced in code (not by prompts): per-state tool allowlists, no write tool without an
approved approval row, four-eyes approvals, persisted steps + audit for every transition,
explicit resume, bounded LLM calls, untrusted document text never drives transitions.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from specbridge import audit, metrics
from specbridge.agent.models import (
    ParsedRequest,
    RetrieveEvidenceArgs,
    SubmitRanking,
)
from specbridge.agent.permissions import MAX_EVIDENCE_CALLS, is_write_tool, tool_allowed
from specbridge.agent.states import TERMINAL, InvalidTransition, State, check_transition
from specbridge.agent.tools import AgentTools, WriteNotApproved
from specbridge.auth.api_keys import Principal
from specbridge.db.models import AgentRun, AgentStep, Approval
from specbridge.erp_client.client import ErpClient, ErpError
from specbridge.errors import (
    BudgetExceededError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    StructuredOutputError,
)
from specbridge.ingestion.embeddings import Embedder
from specbridge.llm.base import LLMRequest, pydantic_tool
from specbridge.llm.usage import LLMService
from specbridge.logging_setup import get_logger
from specbridge.prompts import load_prompt
from specbridge.qa.citations import quote_matches

log = get_logger("specbridge.agent")
MAX_LLM_CALLS = 6
STEP_TIMEOUT_S = 120.0
TRUNC = 3000


class SimulatedCrash(Exception):
    """Raised by the crash hook (tests/scenarios) right after a state is persisted."""


class _Fail(Exception):
    def __init__(self, message: str, retryable: bool = False, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.message, self.retryable, self.extra = message, retryable, extra or {}


class _Escalate(Exception):
    pass


def _trunc(obj: Any) -> Any:
    s = json.dumps(obj, default=str)
    return obj if len(s) <= TRUNC else {"truncated": s[:TRUNC]}


class AgentRunner:
    def __init__(
        self,
        db: Session,
        llm: LLMService,
        erp: ErpClient,
        embedder: Embedder | None = None,
        *,
        step_timeout_s: float = STEP_TIMEOUT_S,
        max_llm_calls: int = MAX_LLM_CALLS,
        crash_after: State | None = None,
    ) -> None:
        self.db, self.llm, self.erp = db, llm, erp
        self.tools = AgentTools(db, erp, embedder)
        self.step_timeout_s, self.max_llm_calls, self.crash_after = (
            step_timeout_s,
            max_llm_calls,
            crash_after,
        )

    # ---------------------------------------------------------------- lifecycle
    def start(self, p: Principal, request_text: str) -> AgentRun:
        run = AgentRun(
            requested_by=p.user,
            requester_role=p.role,
            request_text=request_text,
            state=State.RECEIVED.value,
            result={},
            llm_calls_used=0,
        )
        self.db.add(run)
        self.db.flush()
        audit.record(
            self.db,
            actor=p.user,
            role=p.role,
            action="agent.run_started",
            resource_type="agent_run",
            resource_id=run.id,
            details={"request": request_text[:300]},
        )
        self._commit()
        log.info("agent.state_transition", run_id=str(run.id), to=run.state, frm=None)
        return self.advance(run)

    def resume(self, run_id: uuid.UUID, p: Principal | None = None) -> AgentRun:
        """Explicit resume from the last persisted state (never automatic on startup)."""
        run = self._lock(run_id)
        if State(run.state) in TERMINAL or State(run.state) == State.AWAITING_APPROVAL:
            if State(run.state) == State.AWAITING_APPROVAL:
                return self.advance(run)  # idempotently ensures the approval row exists
            return run
        log.info("agent.resumed", run_id=str(run.id), state=run.state)
        audit.record(
            self.db,
            actor=p.user if p else "system",
            role=p.role if p else None,
            action="agent.resume",
            resource_type="agent_run",
            resource_id=run.id,
            details={"state": run.state},
        )
        return self.advance(run)

    def retry(self, run_id: uuid.UUID, p: Principal) -> AgentRun:
        """Retry a FAILED(retryable) run from COMMITTING."""
        run = self._lock(run_id)
        if State(run.state) != State.FAILED or not (run.result or {}).get("retryable"):
            raise ConflictError("Run is not in a retryable failed state")
        log.info("agent.retry", run_id=str(run.id), actor=p.user)
        self._transition(run, State.COMMITTING, "retry requested", actor=p)
        run.error = None
        self._commit()
        return self.advance(run)

    def _lock(self, run_id: uuid.UUID) -> AgentRun:
        run = self.db.scalar(select(AgentRun).where(AgentRun.id == run_id).with_for_update())
        if run is None:
            raise NotFoundError("Agent run not found")
        return run

    def _commit(self) -> None:
        self.db.commit()

    # --------------------------------------------------------------- transitions
    def _transition(
        self, run: AgentRun, dst: State, reason: str = "", actor: Principal | None = None
    ) -> None:
        src = State(run.state)
        check_transition(src, dst)
        run.state = dst.value
        audit.record(
            self.db,
            actor=actor.user if actor else "agent",
            role=actor.role if actor else None,
            action="agent.state_transition",
            resource_type="agent_run",
            resource_id=run.id,
            details={"from": src.value, "to": dst.value, "reason": reason},
        )
        log.info(
            "agent.state_transition", run_id=str(run.id), frm=src.value, to=dst.value, reason=reason
        )
        if dst in TERMINAL:
            metrics.AGENT_RUNS.labels(dst.value).inc()
            log.info("agent.finished", run_id=str(run.id), state=dst.value)
        self.db.flush()

    def _step(
        self,
        run: AgentRun,
        state: State,
        *,
        tool: str | None = None,
        tool_input: Any = None,
        tool_output: Any = None,
        status: str = "ok",
        attempt: int = 1,
        latency_ms: int = 0,
        error: str | None = None,
    ) -> None:
        n = (
            self.db.scalar(
                select(AgentStep.step_no)
                .where(AgentStep.run_id == run.id)
                .order_by(AgentStep.step_no.desc())
                .limit(1)
            )
            or 0
        ) + 1
        self.db.add(
            AgentStep(
                run_id=run.id,
                step_no=n,
                state=state.value,
                tool_name=tool,
                tool_input=_trunc(tool_input) if tool_input is not None else None,
                tool_output=_trunc(tool_output) if tool_output is not None else None,
                status=status,
                attempt=attempt,
                latency_ms=latency_ms,
                error=error,
            )
        )
        self.db.flush()

    def _fail(
        self, run: AgentRun, msg: str, retryable: bool = False, extra: dict[str, Any] | None = None
    ) -> None:
        run.error = msg
        run.result = {**(run.result or {}), "retryable": retryable, **(extra or {})}
        self._step(run, State(run.state), status="error", error=msg)
        self._transition(run, State.FAILED, msg)

    def _escalate(self, run: AgentRun, msg: str) -> None:
        run.error = msg
        run.result = {**(run.result or {}), "escalation_reason": msg}
        self._step(run, State(run.state), status="error", error=msg)
        self._transition(run, State.ESCALATED, msg)

    # ----------------------------------------------------------------- main loop
    def advance(self, run: AgentRun) -> AgentRun:
        while State(run.state) not in TERMINAL:
            state = State(run.state)
            handler = {
                State.RECEIVED: self._h_received,
                State.PARSE_REQUEST: self._h_parse,
                State.LOOKUP_PART: self._h_lookup,
                State.SEARCH_CANDIDATES: self._h_search,
                State.COMPARE: self._h_compare,
                State.DRAFT_CHANGE_REQUEST: self._h_draft,
                State.AWAITING_APPROVAL: self._h_await,
                State.COMMITTING: self._h_commit,
            }[state]
            t0 = time.perf_counter()
            try:
                nxt = handler(run)
                elapsed = time.perf_counter() - t0
                if elapsed > self.step_timeout_s:
                    raise _Escalate(f"step {state.value} exceeded {self.step_timeout_s:.0f}s")
            except _Fail as f:
                self._fail(run, f.message, f.retryable, f.extra)
                nxt = None
            except _Escalate as e:
                self._escalate(run, str(e))
                nxt = None
            except StructuredOutputError as e:
                self._fail(run, f"The model returned invalid structured output: {e.message}")
                nxt = None
            except BudgetExceededError as e:
                self._fail(run, e.message)
                nxt = None
            except InvalidTransition:
                raise
            except Exception as e:  # unexpected: fail closed, never write
                log.exception("agent.unexpected_error", run_id=str(run.id), state=state.value)
                self._fail(run, f"Unexpected error in {state.value}: {type(e).__name__}")
                nxt = None
            if State(run.state) in TERMINAL:
                self._commit()
                break
            if nxt is None:  # paused (AWAITING_APPROVAL)
                self._commit()
                break
            self._transition(run, nxt)
            self._commit()
            if self.crash_after == nxt:
                raise SimulatedCrash(f"simulated crash after persisting {nxt.value}")
        return run

    # ------------------------------------------------------------------ handlers
    def _h_received(self, run: AgentRun) -> State:
        return State.PARSE_REQUEST

    def _use_llm_call(self, run: AgentRun) -> None:
        if run.llm_calls_used >= self.max_llm_calls:
            raise _Escalate(f"LLM call limit ({self.max_llm_calls}) reached")
        run.llm_calls_used += 1
        self.db.flush()

    def _h_parse(self, run: AgentRun) -> State:
        prompt = load_prompt("agent_parse", 1)
        self._use_llm_call(run)
        t0 = time.perf_counter()
        try:
            parsed = self.llm.structured(
                ParsedRequest,
                tool_name="submit_request",
                tool_description="Submit the parsed replacement request.",
                system=prompt.text,
                messages=[{"role": "user", "content": run.request_text}],
                purpose="agent_parse",
                prompt_version=prompt.label,
                max_tokens=500,
            )
        except StructuredOutputError as exc:
            raise _Fail(
                "I could not understand the request. Please state the part number to "
                "replace and any constraints (e.g. 'Find a replacement for KD-240 that "
                f"supports EtherCAT'). Details: {exc.message[:160]}"
            ) from exc
        run.parsed_request = parsed.model_dump()
        self._step(
            run,
            State.PARSE_REQUEST,
            tool_output=run.parsed_request,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
        return State.LOOKUP_PART

    def _call_tool(
        self, run: AgentRun, state: State, name: str, args: dict[str, Any], fn: Any
    ) -> Any:
        """Allowlist check -> execute -> log. Denied calls never run."""
        if not tool_allowed(state, name):
            self._deny(run, state, name, args)
            raise PermissionError(name)
        t0 = time.perf_counter()
        log.info("agent.tool_call", run_id=str(run.id), tool=name, state=state.value)
        try:
            out = fn()
        except Exception as exc:
            self._step(
                run,
                state,
                tool=name,
                tool_input=args,
                status="error",
                latency_ms=int((time.perf_counter() - t0) * 1000),
                error=str(exc)[:300],
            )
            raise
        self._step(
            run,
            state,
            tool=name,
            tool_input=args,
            tool_output=out,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
        return out

    def _deny(self, run: AgentRun, state: State, name: str, args: Any) -> None:
        run.result = {
            **(run.result or {}),
            "denied_tool_calls": (run.result or {}).get("denied_tool_calls", 0) + 1,
        }
        self._step(
            run,
            state,
            tool=name,
            tool_input=args,
            status="error",
            error=f"tool {name!r} is not allowed in state {state.value}",
        )
        audit.record(
            self.db,
            actor="agent",
            role=None,
            action=f"agent.tool.{name}",
            outcome="denied",
            resource_type="agent_run",
            resource_id=run.id,
            details={"state": state.value, "write_tool": is_write_tool(name)},
        )
        log.warning("agent.tool_denied", run_id=str(run.id), tool=name, state=state.value)

    def _h_lookup(self, run: AgentRun) -> State:
        pr = ParsedRequest.model_validate(run.parsed_request)
        part = self._call_tool(
            run,
            State.LOOKUP_PART,
            "get_part",
            {"part_number": pr.part_number},
            lambda: self.tools.get_part(pr.part_number),
        )
        if part is None:
            raise _Fail(f"Part {pr.part_number!r} was not found in the ERP.")
        run.result = {**(run.result or {}), "original": part}
        return State.SEARCH_CANDIDATES

    def _h_search(self, run: AgentRun) -> State:
        pr = ParsedRequest.model_validate(run.parsed_request)
        original = (run.result or {})["original"]
        cands = self._call_tool(
            run,
            State.SEARCH_CANDIDATES,
            "search_parts",
            {
                "part_number": pr.part_number,
                "constraints": [c.model_dump() for c in pr.constraints],
            },
            lambda: self.tools.search_parts(original, pr.constraints, pr.part_number),
        )
        if not cands:
            raise _Escalate(
                f"No active replacement candidates satisfy the requirements for {pr.part_number} "
                "(same category, covering temperature range, overlapping supply voltage, IP rating "
                "not lower, and all requested constraints). A human should find an alternative."
            )
        run.result = {**(run.result or {}), "candidates": cands}
        return State.COMPARE

    def _h_compare(self, run: AgentRun) -> State:
        res = run.result or {}
        cands, original = res["candidates"], res["original"]
        by_pn = {c["part_number"]: c for c in cands}
        prompt = load_prompt("agent_compare", 1)
        pr = ParsedRequest.model_validate(run.parsed_request)
        user = (
            "<original>\n"
            + json.dumps({"part_number": original["part_number"], "spec": original["spec"]})
            + "\n</original>\n"
            "<constraints>\n"
            + json.dumps([c.model_dump() for c in pr.constraints])
            + "\n</constraints>\n<candidates>\n"
            + json.dumps([{"part_number": c["part_number"], "spec": c["spec"]} for c in cands])
            + "\n</candidates>\nRank the best candidates (max 3)."
        )
        tools = [
            pydantic_tool(
                "retrieve_evidence",
                "Fetch datasheet excerpts for a candidate part.",
                RetrieveEvidenceArgs,
            ),
            pydantic_tool(
                "submit_ranking", "Submit the final ranking with cited claims.", SubmitRanking
            ),
        ]
        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        evidence: dict[str, dict[str, Any]] = {}
        evidence_calls = 0
        for _ in range(self.max_llm_calls):
            self._use_llm_call(run)
            r = self.llm.complete(
                LLMRequest(
                    messages=messages,
                    system=prompt.text,
                    tools=tools,
                    tool_choice={"type": "any"},
                    max_tokens=1500,
                    purpose="agent_compare",
                    prompt_version=prompt.label,
                )
            )
            blocks: list[dict[str, Any]] = [{"type": "text", "text": r.text}] if r.text else []
            blocks += [
                {"type": "tool_use", "id": c.id, "name": c.name, "input": c.input}
                for c in r.tool_calls
            ]
            if not r.tool_calls:
                messages += [
                    {"role": "assistant", "content": r.text or "(no tool call)"},
                    {"role": "user", "content": "Call retrieve_evidence or submit_ranking."},
                ]
                continue
            results: list[dict[str, Any]] = []
            submit = None
            for call in r.tool_calls:
                if call.name == "submit_ranking":
                    submit = call
                    continue
                if not tool_allowed(State.COMPARE, call.name):
                    self._deny(run, State.COMPARE, call.name, call.input)
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "is_error": True,
                            "content": f"Tool {call.name} is not allowed here.",
                        }
                    )
                    continue
                if evidence_calls >= MAX_EVIDENCE_CALLS:
                    self._deny(run, State.COMPARE, call.name, {**call.input, "limit": "max calls"})
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "is_error": True,
                            "content": "Evidence call limit reached.",
                        }
                    )
                    continue
                try:
                    args = RetrieveEvidenceArgs.model_validate(call.input)
                    if args.part_number not in by_pn:
                        raise ValueError("part_number is not a candidate")
                except Exception as exc:
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "is_error": True,
                            "content": f"Invalid arguments: {str(exc)[:200]}",
                        }
                    )
                    continue
                evidence_calls += 1
                chunks = self._call_tool(
                    run,
                    State.COMPARE,
                    "retrieve_evidence",
                    args.model_dump(),
                    lambda a=args: self.tools.retrieve_evidence(a.part_number, a.query),
                )
                for ch in chunks:
                    evidence[ch["chunk_id"]] = {**ch, "part_number": args.part_number}
                body = "\n".join(
                    f'<source chunk_id="{ch["chunk_id"]}" doc="{ch["doc_key"]}" page="{ch["page"]}">\n'
                    f"{ch['content'].replace('</source', '&lt;/source')}\n</source>"
                    for ch in chunks
                )
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": body or "No excerpts found.",
                    }
                )
            if submit is not None:
                ranking = self._validate_ranking(run, submit.input, by_pn, evidence)
                if not ranking:
                    raise _Escalate(
                        "The model could not provide an evidence-backed "
                        "recommendation among the candidates."
                    )
                run.result = {
                    **(run.result or {}),
                    "ranking": ranking,
                    "evidence_calls": evidence_calls,
                }
                self._step(run, State.COMPARE, tool_output={"ranking": ranking})
                return State.DRAFT_CHANGE_REQUEST
            messages += [
                {"role": "assistant", "content": blocks},
                {"role": "user", "content": results},
            ]
        raise _Escalate("The model did not submit a ranking within the allowed number of calls.")

    def _validate_ranking(
        self,
        run: AgentRun,
        raw: dict[str, Any],
        by_pn: dict[str, Any],
        evidence: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        try:
            sub = SubmitRanking.model_validate(raw)
        except Exception as exc:
            log.warning("agent.ranking_invalid", error=str(exc)[:200])
            return []
        out: list[dict[str, Any]] = []
        for rc in sub.ranking:
            if rc.part_number not in by_pn:
                log.warning(
                    "agent.candidate_dropped", part=rc.part_number, reason="not a candidate"
                )
                continue
            claims, ev = [], []
            for cl in rc.claims:
                valid = [
                    c
                    for c in cl.citations
                    if c.chunk_id in evidence
                    and evidence[c.chunk_id]["part_number"] == rc.part_number
                    and quote_matches(c.quote, evidence[c.chunk_id]["content"])
                ]
                if not valid:
                    log.warning("agent.claim_removed", part=rc.part_number, claim=cl.text[:80])
                    continue
                claims.append(cl.text)
                for c in valid:
                    e = evidence[c.chunk_id]
                    ev.append(
                        {
                            "chunk_id": c.chunk_id,
                            "doc_key": e["doc_key"],
                            "page": e["page"],
                            "quote": c.quote,
                        }
                    )
            if not claims:
                log.warning(
                    "agent.candidate_dropped", part=rc.part_number, reason="no verified claim"
                )
                continue
            out.append(
                {"part_number": rc.part_number, "rationale": " ".join(claims), "evidence": ev}
            )
        return out[:3]

    def _h_draft(self, run: AgentRun) -> State:
        res = run.result or {}
        top = res["ranking"][0]
        cr = {
            "original_part": res["original"]["part_number"],
            "proposed_part": top["part_number"],
            "rationale": top["rationale"],
            "evidence": top["evidence"],
            "requested_by": run.requested_by,
        }
        run.result = {**res, "change_request": cr}
        self._step(run, State.DRAFT_CHANGE_REQUEST, tool_output=cr)
        return State.AWAITING_APPROVAL

    def _h_await(self, run: AgentRun) -> State | None:
        existing = self.db.scalar(select(Approval).where(Approval.run_id == run.id))
        if existing is None:
            cr = (run.result or {})["change_request"]
            self.db.add(
                Approval(
                    run_id=run.id,
                    change_request=cr,
                    status="pending",
                    requested_by=run.requested_by,
                )
            )
            self.db.flush()
            self._step(run, State.AWAITING_APPROVAL, tool_output={"approval": "pending"})
            audit.record(
                self.db,
                actor="agent",
                role=None,
                action="approval.requested",
                resource_type="agent_run",
                resource_id=run.id,
                details={"proposed_part": cr["proposed_part"]},
            )
            log.info("agent.paused_for_approval", run_id=str(run.id))
        return None

    def _h_commit(self, run: AgentRun) -> State:
        cr = (run.result or {})["change_request"]
        approval = self.db.scalar(select(Approval).where(Approval.run_id == run.id))
        body = {**cr, "approved_by": approval.decided_by if approval else None}
        t0 = time.perf_counter()
        try:
            resp = self._call_tool(
                run,
                State.COMMITTING,
                "create_change_request",
                cr,
                lambda: self.tools.create_change_request(run.id, body),
            )
        except WriteNotApproved as exc:
            raise _Fail(f"Write blocked: {exc}") from exc
        except ErpError as exc:
            self._step(
                run,
                State.COMMITTING,
                tool="create_change_request",
                status="retried",
                attempt=self.erp.attempts,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                error=str(exc)[:300],
            )
            raise _Fail(
                f"ERP unavailable while creating the change request: {exc}",
                retryable=exc.retryable,
                extra={"failed_stage": "COMMITTING"},
            ) from exc
        run.result = {**(run.result or {}), "erp_change_request": resp, "retryable": False}
        run.error = None
        return State.DONE

    # ------------------------------------------------------------------ approvals
    def decide(
        self, approval_id: uuid.UUID, p: Principal, approve: bool, comment: str = ""
    ) -> Approval:
        appr = self.db.scalar(select(Approval).where(Approval.id == approval_id).with_for_update())
        if appr is None:
            raise NotFoundError("Approval not found")
        if appr.status != "pending":
            raise ConflictError(f"Approval already {appr.status}")
        if p.user == appr.requested_by:
            audit.record_denied(
                p.user,
                p.role,
                "approval.decide",
                "approval",
                appr.id,
                {"reason": "four-eyes: approver must differ from requester"},
            )
            log.warning("auth.denied", actor=p.user, reason="four_eyes", approval=str(appr.id))
            raise ForbiddenError("Four-eyes rule: you cannot decide your own request.")
        run = self._lock(appr.run_id)
        if State(run.state) != State.AWAITING_APPROVAL:
            raise ConflictError(f"Run is in state {run.state}, not awaiting approval")
        from datetime import UTC, datetime

        appr.status = "approved" if approve else "rejected"
        appr.decided_by, appr.decided_at, appr.comment = p.user, datetime.now(UTC), comment
        audit.record(
            self.db,
            actor=p.user,
            role=p.role,
            action="approval.decided",
            resource_type="approval",
            resource_id=appr.id,
            details={"decision": appr.status, "run_id": str(run.id), "comment": comment[:200]},
        )
        log.info("approval.decided", approval=str(appr.id), decision=appr.status, actor=p.user)
        if approve:
            self._transition(run, State.COMMITTING, f"approved by {p.user}", actor=p)
            self._commit()
            self.advance(run)
        else:
            run.result = {**(run.result or {}), "rejected_by": p.user, "comment": comment}
            self._transition(run, State.REJECTED, f"rejected by {p.user}", actor=p)
            self._commit()
        return appr
