import pytest
from pydantic import ValidationError

from specbridge.agent.fake import parse_handler
from specbridge.agent.models import Constraint, ParsedRequest, SubmitRanking
from specbridge.agent.permissions import ALLOWLIST, WRITE_TOOLS, is_write_tool, tool_allowed
from specbridge.agent.states import (
    TERMINAL,
    TRANSITIONS,
    InvalidTransition,
    State,
    check_transition,
)
from specbridge.agent.tools import check_constraint
from specbridge.extraction.fields import AGENT_CONSTRAINT_FIELDS
from specbridge.llm.base import LLMRequest


def test_every_state_has_transitions_and_allowlist():
    assert set(TRANSITIONS) == set(State) == set(ALLOWLIST)


def test_happy_path_chain_is_allowed():
    chain = [
        State.RECEIVED,
        State.PARSE_REQUEST,
        State.LOOKUP_PART,
        State.SEARCH_CANDIDATES,
        State.COMPARE,
        State.DRAFT_CHANGE_REQUEST,
        State.AWAITING_APPROVAL,
        State.COMMITTING,
        State.DONE,
    ]
    for a, b in zip(chain, chain[1:], strict=False):
        check_transition(a, b)


@pytest.mark.parametrize(
    "src,dst",
    [
        (State.RECEIVED, State.COMMITTING),  # cannot skip to the write
        (State.COMPARE, State.COMMITTING),
        (State.DRAFT_CHANGE_REQUEST, State.COMMITTING),  # must pass AWAITING_APPROVAL
        (State.DONE, State.RECEIVED),
        (State.REJECTED, State.COMMITTING),
        (State.ESCALATED, State.COMMITTING),
        (State.AWAITING_APPROVAL, State.DONE),
    ],
)
def test_illegal_transitions(src, dst):
    with pytest.raises(InvalidTransition):
        check_transition(src, dst)


def test_only_awaiting_approval_and_failed_lead_to_committing():
    sources = {s for s, dsts in TRANSITIONS.items() if State.COMMITTING in dsts}
    assert sources == {State.AWAITING_APPROVAL, State.FAILED}
    assert {State.DONE, State.REJECTED, State.FAILED, State.ESCALATED} == TERMINAL
    for t in (State.DONE, State.REJECTED, State.ESCALATED):
        assert not TRANSITIONS[t]


def test_allowlist_matches_spec():
    assert ALLOWLIST[State.LOOKUP_PART] == {"get_part"}
    assert ALLOWLIST[State.SEARCH_CANDIDATES] == {"search_parts"}
    assert ALLOWLIST[State.COMPARE] == {"retrieve_evidence"}
    assert ALLOWLIST[State.COMMITTING] == {"create_change_request"}
    for s in State:
        if s != State.COMMITTING:
            assert not (ALLOWLIST[s] & WRITE_TOOLS)  # write tool only ever allowed in COMMITTING
    assert tool_allowed(State.COMMITTING, "create_change_request")
    assert not tool_allowed(State.COMPARE, "create_change_request")
    assert not tool_allowed(State.COMPARE, "search_parts") and is_write_tool(
        "create_change_request"
    )


def test_parsed_request_validation():
    ok = ParsedRequest.model_validate(
        {
            "part_number": " KD-240 ",
            "constraints": [{"field": "interfaces", "op": "contains", "value": "IO-Link"}],
        }
    )
    assert ok.part_number == "KD-240"
    for bad in (
        {"part_number": "KD-240", "constraints": [{"field": "color", "op": "eq", "value": 1}]},
        {
            "part_number": "KD-240",
            "constraints": [{"field": "ip_rating", "op": "like", "value": "x"}],
        },
        {"part_number": "; DROP TABLE parts;--"},
        {"part_number": ""},
    ):
        with pytest.raises(ValidationError):
            ParsedRequest.model_validate(bad)
    assert set(AGENT_CONSTRAINT_FIELDS) >= {"interfaces", "ip_rating", "category"}


def test_ranking_max_three():
    with pytest.raises(ValidationError):
        SubmitRanking.model_validate({"ranking": [{"part_number": f"P-{i}"} for i in range(4)]})


def test_check_constraint_semantics():
    spec = {
        "interfaces": ["IO-Link", "PROFINET"],
        "ip_rating": "IP67",
        "operating_temp_max_c": 85,
        "category": "sensor",
        "certifications": ["CE", "UL"],
        "weight_g": None,
    }
    c = lambda f, op, v: check_constraint(spec, Constraint(field=f, op=op, value=v))  # noqa: E731
    assert c("interfaces", "contains", "io link") and not c("interfaces", "contains", "EtherCAT")
    assert c("ip_rating", "gte", "IP65") and c("ip_rating", "gte", "IP67")
    assert not c("ip_rating", "gte", "IP69K") and c("ip_rating", "eq", "IP 67")
    assert c("operating_temp_max_c", "gte", 80) and not c("operating_temp_max_c", "gte", 90)
    assert c("operating_temp_max_c", "lte", 85) and c("category", "eq", "Sensor")
    assert c("certifications", "contains", "UL Listed") and not c("weight_g", "lte", 100)


def test_fake_parse_handler():
    def parse(t):
        return parse_handler(LLMRequest(messages=[{"role": "user", "content": t}]))

    r = parse("Find a replacement for NS-IND-1200, it needs IO-Link and IP67")
    assert r["part_number"] == "NS-IND-1200"
    assert {"field": "interfaces", "op": "contains", "value": "IO-Link"} in r["constraints"]
    assert {"field": "ip_rating", "op": "gte", "value": "IP67"} in r["constraints"]
    assert parse("replace KD-240 with EtherCAT drive")["constraints"][0]["value"] == "EtherCAT"
