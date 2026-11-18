# 0002 - Explicit, persisted state machine instead of an agent framework

## Context
The part-substitution agent may eventually write to an ERP. A reviewer must be able to answer "what
could this agent possibly do, and what stops it?" without reading prompts. Document text is
untrusted and a prompt-injection datasheet is part of the corpus.

## Options considered
1. A tool-calling agent loop / framework (LangChain, LangGraph, a ReAct loop).
2. A hand-written state machine (`RECEIVED -> ... -> DONE`) where the LLM fills in two bounded steps.

## Decision
Option 2. States, the transition table, per-state tool allowlists and the write guard live in code
(`specbridge/agent/{states,permissions,tools,runner}.py`). The LLM is only used to (a) parse the
request into a validated schema and (b) rank already-vetted candidates with cited evidence.
Candidate search is a deterministic parameterised SQL query. Every transition and tool call is
persisted (`agent_steps`, `audit_log`), so a run can be resumed explicitly after a crash.

## Consequences
- Safety does not depend on the model behaving: scenarios S10/S12 script a *compromised* model that
  tries a forbidden write; it is denied by the allowlist and the approval gate, and the ERP stays untouched.
- Mutation checks (removing the allowlist entry, the four-eyes check, the discontinued filter or the
  stable idempotency key) each make a scenario fail - see the journal entries for 4.2.
- Less flexible than a free-form agent: new capabilities need a new state and allowlist entry.
