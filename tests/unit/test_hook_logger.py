import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "dev" / "log_tool_call.py"


def run(stdin: str, project_dir: Path, env_extra: dict[str, str] | None = None):
    import os

    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project_dir), **(env_extra or {})}
    return subprocess.run(
        [sys.executable, str(SCRIPT)], input=stdin, text=True, capture_output=True, env=env
    )


def test_writes_and_truncates(tmp_path):
    payload = {
        "session_id": "s",
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_response": "x" * 5000,
    }
    r = run(json.dumps(payload), tmp_path)
    assert r.returncode == 0
    line = (tmp_path / "logs/dev/claude_tool_calls.jsonl").read_text().strip()
    rec = json.loads(line)
    assert rec["tool_name"] == "Bash" and len(rec["tool_response"]) == 2000


def test_redaction(tmp_path):
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo sk-ant-abc123_XYZ AKIAABCDEFGHIJKLMNOP"},
        "tool_response": "aws_secret_access_key = hunter2 and MYKEY123",
    }
    r = run(json.dumps(payload), tmp_path, {"ANTHROPIC_API_KEY": "MYKEY123"})
    assert r.returncode == 0
    text = (tmp_path / "logs/dev/claude_tool_calls.jsonl").read_text()
    for s in ("sk-ant-abc123", "AKIAABCDEFGHIJKLMNOP", "hunter2", "MYKEY123"):
        assert s not in text


def test_always_exits_zero_on_garbage(tmp_path):
    assert run("not json{{{", tmp_path).returncode == 0
    assert run("", tmp_path).returncode == 0
