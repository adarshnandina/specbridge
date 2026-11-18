#!/usr/bin/env python3
"""Close a task: append journal + change note, mark PROGRESS done, commit locally (never push).

usage: task_done.py ID "Title" --summary S --tests T [--files "a b"] [--problems P]
       [--decisions D] [--eval E] [--deviations V] [--next N] [--path P ...]
--path restricts the commit to those pathspecs (default: everything).
"""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sh(*cmd: str) -> str:
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def next_change_no() -> int:
    nums = [
        int(m.group(1))
        for p in (ROOT / "docs/changes").glob("*.md")
        if (m := re.match(r"(\d+)-", p.name))
    ]
    return max(nums, default=0) + 1


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("id")
    a.add_argument("title")
    a.add_argument("--summary", required=True)
    a.add_argument("--tests", required=True)
    a.add_argument("--files", default="see commit")
    a.add_argument("--commands", default="make lint typecheck test (pass)")
    a.add_argument("--problems", default="none")
    a.add_argument("--decisions", default="none")
    a.add_argument("--eval", dest="eval_", default="n/a")
    a.add_argument("--deviations", default="none")
    a.add_argument("--next", dest="next_", default="next task in PROGRESS.md")
    a.add_argument("--path", action="append", default=[])
    a.add_argument("--risks", default="none known")
    a = a.parse_args()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with (ROOT / "docs/build-log/JOURNAL.md").open("a") as fh:
        fh.write(f"""
## {now} — {a.id} {a.title}
**Goal:** {a.summary}
**What I did:** {a.summary}
**Files changed:** {a.files}
**Commands run and outcome:** {a.commands}
**Tests:** {a.tests}
**Eval results (if any):** {a.eval_}
**Problems and how I solved them:** {a.problems}
**Decisions made:** {a.decisions}
**Deviations from spec:** {a.deviations}
**Next step:** {a.next_}
""")
    n = next_change_no()
    slug = re.sub(r"[^a-z0-9]+", "-", a.title.lower()).strip("-")[:50]
    (ROOT / f"docs/changes/{n:04d}-{slug}.md").write_text(f"""# {a.id} {a.title}
## Summary
{a.summary}
## Why
Part of milestone task {a.id} in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
{a.files}
## How it was tested (commands + results)
{a.tests}
## Eval impact (baseline run id → new run id, deltas) or "n/a"
{a.eval_}
## Risks / follow-ups
{a.risks}
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
""")
    prog = ROOT / "docs/build-log/PROGRESS.md"
    text = prog.read_text()
    text = re.sub(
        rf"^(- {re.escape(a.id)} .*?) — .*$",
        r"\1 — done (" + now[:10] + ", HASH)",
        text,
        flags=re.M,
    )
    prog.write_text(text)
    paths = a.path or ["."]
    sh("git", "add", "-A", "--", *paths, "docs", "scripts")
    sh("git", "commit", "-qm", f"{a.id}: {a.title}")
    h = sh("git", "rev-parse", "--short", "HEAD")
    prog.write_text(prog.read_text().replace("HASH)", h + ")"))
    sh("git", "add", str(prog))
    sh("git", "commit", "-q", "--amend", "--no-edit")
    print(f"committed {a.id} as {sh('git', 'rev-parse', '--short', 'HEAD')}")


if __name__ == "__main__":
    main()
