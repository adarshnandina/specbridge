import json
import time

import pytest
from sqlalchemy import select

from specbridge.agent.runner import AgentRunner
from specbridge.agent.scenarios import AgentEnv
from specbridge.agent.states import State
from specbridge.agent.tools import AgentTools, WriteNotApproved
from specbridge.auth.api_keys import Principal
from specbridge.config import Settings
from specbridge.db.models import AgentRun, AgentStep, Approval, AuditLog
from specbridge.db.session import session_scope
from specbridge.erp_client.client import ErpClient
from specbridge.ingestion.embeddings import get_embedder
from specbridge.llm.base import LLMResult, ToolCall
from specbridge.llm.budget import BudgetGuard
from specbridge.llm.fake_handlers import register_all_handlers
from specbridge.llm.fake_provider import FakeProvider
from specbridge.llm.usage import LLMService, MemoryLedger

pytestmark = pytest.mark.integration
BOB = Principal("bob", "engineer")
CAROL = Principal("carol", "approver")


@pytest.fixture(scope="module")
def env(pg_url, synth_dir, tmp_path_factory):
    e = AgentEnv(synth_dir, get_embedder(), tmp_path_factory.mktemp("erp") / "erp.sqlite")
    e.prepare()
    return e


@pytest.fixture
def ctx(env):
    env._reset_between()
    provider = register_all_handlers(FakeProvider())
    ledger = MemoryLedger()
    llm = LLMService(
        provider,
        settings=Settings(_env_file=None, log_llm_payloads=False),
        recorder=ledger.record,
        budget=BudgetGuard(5, ledger.spent),
    )
    erp = ErpClient(env.erp_http, wait_initial=0.001, wait_max=0.005)
    return {"env": env, "provider": provider, "llm": llm, "erp": erp, "ledger": ledger}


def runner(ctx, s, **kw):
    return AgentRunner(s, ctx["llm"], ctx["erp"], get_embedder(), **kw)


REQ = "Find a replacement for discontinued part KD-240"


def test_write_tool_refuses_without_approved_approval(ctx):
    with session_scope() as s:
        run = runner(ctx, s).start(BOB, REQ)
        assert run.state == "AWAITING_APPROVAL"
        tools = AgentTools(s, ctx["erp"])
        with pytest.raises(WriteNotApproved):
            tools.create_change_request(
                run.id, {"original_part": "KD-240", "proposed_part": "KD-210"}
            )
        assert ctx["env"].erp_http.get("/change-requests").json() == []


def test_steps_and_audit_are_persisted_for_every_transition(ctx):
    with session_scope() as s:
        run = runner(ctx, s).start(BOB, REQ)
        steps = s.scalars(
            select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.step_no)
        ).all()
        assert [x.step_no for x in steps] == list(range(1, len(steps) + 1))
        assert {"get_part", "search_parts", "retrieve_evidence"} <= {x.tool_name for x in steps}
        trans = [
            a.details["to"]
            for a in s.scalars(
                select(AuditLog)
                .where(AuditLog.action == "agent.state_transition")
                .order_by(AuditLog.ts)
            )
        ]
        assert trans == [
            "PARSE_REQUEST",
            "LOOKUP_PART",
            "SEARCH_CANDIDATES",
            "COMPARE",
            "DRAFT_CHANGE_REQUEST",
            "AWAITING_APPROVAL",
        ]
        assert run.llm_calls_used == 3  # parse + 2 compare turns


def test_evidence_call_cap_and_denial(ctx):
    four = [
        ToolCall("retrieve_evidence", {"part_number": "KD-210", "query": f"q{i}"}, f"toolu_e{i}")
        for i in range(4)
    ]
    ctx["provider"].script("agent_compare", LLMResult(tool_calls=four))  # 4 calls in one turn
    with session_scope() as s:
        run = runner(ctx, s).start(BOB, REQ)
        # first 3 evidence calls executed, 4th denied; model then needs another turn (default
        # handler is re-used and submits a ranking using the results)
        assert (run.result or {}).get("denied_tool_calls", 0) >= 1
        ok = s.scalars(
            select(AgentStep).where(
                AgentStep.run_id == run.id,
                AgentStep.tool_name == "retrieve_evidence",
                AgentStep.status == "ok",
            )
        ).all()
        assert len(ok) == 3


def test_llm_call_limit_escalates(ctx):
    # the model never submits a ranking: keeps asking for evidence on a stubbed loop
    never = ToolCall("retrieve_evidence", {"part_number": "KD-210", "query": "x"}, "toolu_e0")
    ctx["provider"].register("agent_compare", lambda req: LLMResult(tool_calls=[never]))
    with session_scope() as s:
        run = runner(ctx, s).start(BOB, REQ)
        assert run.state == "ESCALATED" and run.llm_calls_used == 6
        assert "limit" in (run.error or "") or "ranking" in (run.error or "")
        assert ctx["env"].erp_http.get("/change-requests").json() == []


def test_hallucinated_part_and_uncited_claims_are_dropped(ctx):
    def handler(req):
        last = req.messages[-1]["content"]
        if not (isinstance(last, list) and any(b.get("type") == "tool_result" for b in last)):
            return {
                "text": "",
                "tool_calls": [
                    {
                        "name": "retrieve_evidence",
                        "id": "toolu_e0",
                        "input": {"part_number": "KD-210", "query": "temperature"},
                    }
                ],
            }
        import re

        m = re.search(
            r'<source chunk_id="([^"]+)"[^>]*>\n(.*?)\n</source>', last[0]["content"], re.S
        )
        line = next(ln for ln in m.group(2).split("\n") if len(ln) > 8)
        return {
            "text": "",
            "tool_calls": [
                {
                    "name": "submit_ranking",
                    "id": "s",
                    "input": {
                        "ranking": [
                            {
                                "part_number": "ZZ-999",
                                "claims": [
                                    {
                                        "text": "invented part",
                                        "citations": [{"chunk_id": m.group(1), "quote": line}],
                                    }
                                ],
                            },
                            {
                                "part_number": "KD-210",
                                "claims": [
                                    {"text": "uncited claim", "citations": []},
                                    {
                                        "text": "fabricated quote",
                                        "citations": [
                                            {
                                                "chunk_id": m.group(1),
                                                "quote": "totally made up sentence about 9000 V",
                                            }
                                        ],
                                    },
                                    {
                                        "text": "good claim",
                                        "citations": [{"chunk_id": m.group(1), "quote": line}],
                                    },
                                ],
                            },
                        ]
                    },
                }
            ],
        }

    ctx["provider"].register("agent_compare", handler)
    with session_scope() as s:
        run = runner(ctx, s).start(BOB, REQ)
        rank = run.result["ranking"]
        assert [r["part_number"] for r in rank] == ["KD-210"]
        assert rank[0]["rationale"] == "good claim" and len(rank[0]["evidence"]) == 1
        assert run.state == "AWAITING_APPROVAL"


def test_no_verified_evidence_escalates(ctx):
    def handler(req):
        return {
            "text": "",
            "tool_calls": [
                {
                    "name": "submit_ranking",
                    "id": "s",
                    "input": {
                        "ranking": [
                            {
                                "part_number": "KD-210",
                                "claims": [{"text": "no evidence", "citations": []}],
                            }
                        ]
                    },
                }
            ],
        }

    ctx["provider"].register("agent_compare", handler)
    with session_scope() as s:
        run = runner(ctx, s).start(BOB, REQ)
        assert run.state == "ESCALATED" and ctx["env"].erp_http.get("/change-requests").json() == []


def test_step_timeout_escalates(ctx, monkeypatch):
    orig = AgentTools.search_parts

    def slow(self, *a, **k):
        time.sleep(0.05)
        return orig(self, *a, **k)

    monkeypatch.setattr(AgentTools, "search_parts", slow)
    with session_scope() as s:
        run = runner(ctx, s, step_timeout_s=0.01).start(BOB, REQ)
        assert run.state == "ESCALATED" and "exceeded" in run.error


def test_resume_is_explicit_and_idempotent(ctx):
    with session_scope() as s:
        r = runner(ctx, s, crash_after=State.SEARCH_CANDIDATES)
        from specbridge.agent.runner import SimulatedCrash

        with pytest.raises(SimulatedCrash):
            r.start(BOB, REQ)
    with session_scope() as s:
        run = s.scalars(select(AgentRun)).one()
        assert run.state == "SEARCH_CANDIDATES"  # persisted, NOT auto-resumed
        done = runner(ctx, s).resume(run.id, BOB)
        assert done.state == "AWAITING_APPROVAL"
        runner(ctx, s).resume(run.id, BOB)  # second resume changes nothing
        assert len(s.scalars(select(Approval)).all()) == 1


def test_approval_flow_four_eyes_and_double_decision(ctx):
    from specbridge.errors import ConflictError, ForbiddenError

    with session_scope() as s:
        run = runner(ctx, s).start(BOB, REQ)
        appr = s.scalars(select(Approval)).one()
        with pytest.raises(ForbiddenError):
            runner(ctx, s).decide(appr.id, BOB, True)  # requester cannot decide
    with session_scope() as s:
        appr = s.scalars(select(Approval)).one()
        assert appr.status == "pending"
        denied = s.scalars(select(AuditLog).where(AuditLog.outcome == "denied")).all()
        assert denied and denied[0].actor == "bob"
        runner(ctx, s).decide(appr.id, CAROL, True, "ok")
    with session_scope() as s:
        run = s.scalars(select(AgentRun)).one()
        assert run.state == "DONE" and run.result["erp_change_request"]["status"] == "created"
        with pytest.raises(ConflictError):
            runner(ctx, s).decide(s.scalars(select(Approval)).one().id, CAROL, True)
    assert json.dumps(ctx["env"].erp_http.get("/change-requests").json()).count("KD-240") >= 1
