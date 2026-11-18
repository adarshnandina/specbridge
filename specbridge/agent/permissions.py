"""Per-state tool allowlists and the write-tool guard."""

from __future__ import annotations

from specbridge.agent.states import State

READ_TOOLS = frozenset({"get_part", "search_parts", "retrieve_evidence"})
WRITE_TOOLS = frozenset({"create_change_request"})

ALLOWLIST: dict[State, frozenset[str]] = {
    State.RECEIVED: frozenset(),
    State.PARSE_REQUEST: frozenset(),
    State.LOOKUP_PART: frozenset({"get_part"}),
    State.SEARCH_CANDIDATES: frozenset({"search_parts"}),
    State.COMPARE: frozenset({"retrieve_evidence"}),
    State.DRAFT_CHANGE_REQUEST: frozenset(),
    State.AWAITING_APPROVAL: frozenset(),
    State.COMMITTING: frozenset({"create_change_request"}),
    State.DONE: frozenset(),
    State.REJECTED: frozenset(),
    State.FAILED: frozenset(),
    State.ESCALATED: frozenset(),
}
MAX_EVIDENCE_CALLS = 3


def tool_allowed(state: State, tool: str) -> bool:
    return tool in ALLOWLIST.get(state, frozenset())


def is_write_tool(tool: str) -> bool:
    return tool in WRITE_TOOLS
