# 0.2 Hook logger and settings
## Summary
Claude Code hook script logging redacted tool calls to logs/dev, plus .claude/settings.json
## Why
Part of milestone task 0.2 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
scripts/dev/log_tool_call.py .claude/settings.json tests/unit/test_hook_logger.py
## How it was tested (commands + results)
3 passed (tests/unit/test_hook_logger.py: truncation, redaction, always exit 0)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
