import json

from typer.testing import CliRunner

from specbridge.cli import app

runner = CliRunner()


def test_logs_tail_filters_by_event_glob(tmp_path):
    f = tmp_path / "app.jsonl"
    rows = [
        {"event": "agent.state_transition", "n": 1},
        {"event": "http.request", "n": 2},
        {"event": "agent.tool_denied", "n": 3},
        {"event": "qa.answered", "n": 4},
    ]
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
    r = runner.invoke(app, ["logs", "tail", "--file", str(f), "--event", "agent.*"])
    assert r.exit_code == 0
    got = [json.loads(ln)["n"] for ln in r.stdout.strip().splitlines()]
    assert got == [1, 3]
    r2 = runner.invoke(app, ["logs", "tail", "--file", str(f), "-n", "2"])
    assert r2.exit_code == 0 and len([ln for ln in r2.stdout.splitlines() if ln]) == 2


def test_logs_tail_missing_file(tmp_path):
    r = runner.invoke(app, ["logs", "tail", "--file", str(tmp_path / "nope.jsonl")])
    assert r.exit_code == 1


def test_cli_has_expected_commands():
    out = runner.invoke(app, ["--help"]).stdout
    for cmd in ("ingest", "eval", "agent", "logs"):
        assert cmd in out
    assert "gate" in runner.invoke(app, ["eval", "--help"]).stdout
    assert "resume" in runner.invoke(app, ["agent", "--help"]).stdout
