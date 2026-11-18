#!/usr/bin/env python3
"""Claude Code hook: append one redacted JSON line per tool call / prompt. Always exits 0."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"aws_secret_access_key\s*=\s*\S+", re.IGNORECASE),
]
MAX_RESPONSE = 2000


def redact(text: str, extra_secrets: list[str] | None = None) -> str:
    for p in PATTERNS:
        text = p.sub("[REDACTED]", text)
    for s in extra_secrets or []:
        if s:
            text = text.replace(s, "[REDACTED]")
    return text


def build_record(payload: dict, env: dict[str, str] | None = None) -> dict:
    env = env if env is not None else dict(os.environ)
    secrets = [env.get("ANTHROPIC_API_KEY", "")]
    response = payload.get("tool_response")
    if response is not None and not isinstance(response, str):
        response = json.dumps(response, default=str)
    rec = {
        "ts": datetime.now(UTC).isoformat(),
        "session_id": payload.get("session_id"),
        "hook_event_name": payload.get("hook_event_name"),
        "tool_name": payload.get("tool_name"),
        "tool_input": payload.get("tool_input"),
        "tool_response": (response or "")[:MAX_RESPONSE] if response is not None else None,
    }
    if payload.get("prompt") is not None:
        rec["prompt"] = payload["prompt"]
    return json.loads(redact(json.dumps(rec, default=str), secrets))


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        rec = build_record(payload)
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
        out = root / "logs" / "dev" / "claude_tool_calls.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
    except Exception:  # noqa: BLE001 - must never block Claude Code
        pass
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except BaseException:  # noqa: BLE001
        code = 0
    sys.exit(0 if code is None else 0)
