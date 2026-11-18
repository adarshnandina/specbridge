"""Explicit agent state machine."""

from __future__ import annotations

from enum import StrEnum


class State(StrEnum):
    RECEIVED = "RECEIVED"
    PARSE_REQUEST = "PARSE_REQUEST"
    LOOKUP_PART = "LOOKUP_PART"
    SEARCH_CANDIDATES = "SEARCH_CANDIDATES"
    COMPARE = "COMPARE"
    DRAFT_CHANGE_REQUEST = "DRAFT_CHANGE_REQUEST"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMMITTING = "COMMITTING"
    DONE = "DONE"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


TERMINAL = frozenset({State.DONE, State.REJECTED, State.FAILED, State.ESCALATED})
S = State
_ALWAYS = {S.FAILED, S.ESCALATED}

TRANSITIONS: dict[State, frozenset[State]] = {
    S.RECEIVED: frozenset({S.PARSE_REQUEST} | _ALWAYS),
    S.PARSE_REQUEST: frozenset({S.LOOKUP_PART} | _ALWAYS),
    S.LOOKUP_PART: frozenset({S.SEARCH_CANDIDATES} | _ALWAYS),
    S.SEARCH_CANDIDATES: frozenset({S.COMPARE} | _ALWAYS),
    S.COMPARE: frozenset({S.DRAFT_CHANGE_REQUEST} | _ALWAYS),
    S.DRAFT_CHANGE_REQUEST: frozenset({S.AWAITING_APPROVAL} | _ALWAYS),
    S.AWAITING_APPROVAL: frozenset({S.COMMITTING, S.REJECTED} | _ALWAYS),
    # FAILED(retryable) -> COMMITTING is the explicit retry edge (see runner.retry)
    S.COMMITTING: frozenset({S.DONE} | _ALWAYS),
    S.DONE: frozenset(),
    S.REJECTED: frozenset(),
    S.FAILED: frozenset({S.COMMITTING}),
    S.ESCALATED: frozenset(),
}


class InvalidTransition(Exception):
    pass


def check_transition(src: State, dst: State) -> None:
    if dst not in TRANSITIONS[src]:
        raise InvalidTransition(f"{src} -> {dst} is not allowed")
