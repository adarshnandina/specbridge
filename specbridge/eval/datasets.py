"""Dataset loaders and validation for eval/datasets/*."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

DATASET_DIR = Path("eval/datasets")
MIN_COUNTS = {
    "factual": 35,
    "table_lookup": 20,
    "cross_doc": 15,
    "revision": 8,
    "unanswerable": 15,
    "injection": 5,
    "open": 10,
}
MATCHES = ("exact", "numeric", "set", "contains", "judge")


class SourceRef(BaseModel):
    doc_key: str
    pages: list[int] = Field(default_factory=list)


class QAItem(BaseModel):
    id: str
    split: Literal["dev", "test"]
    type: Literal[
        "factual", "table_lookup", "cross_doc", "revision", "unanswerable", "injection", "open"
    ]
    question: str
    expected_answer: Any = None
    match: Literal["exact", "numeric", "set", "contains", "judge"]
    expected_sources: list[SourceRef] = Field(default_factory=list)
    unit: str | None = None
    tolerance: float | None = None
    expect_abstain: bool = False
    forbidden: list[str] = Field(default_factory=list)
    superseded_value: Any = None
    note: str | None = None
    reason: str | None = None


def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_qa(path: Path | str = DATASET_DIR / "qa.jsonl", split: str | None = None) -> list[QAItem]:
    items = [QAItem.model_validate(r) for r in read_jsonl(path)]
    return [i for i in items if split in (None, "all") or i.split == split]


def file_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dataset_hashes(dataset_dir: Path = DATASET_DIR) -> dict[str, str]:
    return {p.name: file_sha256(p) for p in sorted(dataset_dir.glob("*")) if p.is_file()}


def validate_datasets(dataset_dir: Path = DATASET_DIR) -> list[str]:
    """Return a list of problems (empty = valid)."""
    problems: list[str] = []
    gt = read_jsonl(dataset_dir / "extraction_synthetic.jsonl")
    keys = {r["doc_key"]: r for r in gt}
    qa = load_qa(dataset_dir / "qa.jsonl")
    ids = [q.id for q in qa]
    if len(set(ids)) != len(ids):
        problems.append("duplicate qa ids")
    qs = [q.question for q in qa]
    if len(set(qs)) != len(qs):
        problems.append("duplicate qa questions")
    counts: Counter[str] = Counter(q.type for q in qa)
    for t, n in MIN_COUNTS.items():
        if counts[t] < n:
            problems.append(f"type {t}: {counts[t]} < required {n}")
    if len(qa) < 100:
        problems.append(f"only {len(qa)} qa items (<100)")
    test_frac = sum(q.split == "test" for q in qa) / max(len(qa), 1)
    if not 0.3 <= test_frac <= 0.5:
        problems.append(f"test split fraction {test_frac:.2f} outside 0.3-0.5")
    for q in qa:
        for s in q.expected_sources:
            rec = keys.get(s.doc_key)
            if rec is None:
                problems.append(f"{q.id}: unknown doc_key {s.doc_key}")
                continue
            pc = max(rec["pages"].values())
            if any(p < 1 or p > 2 for p in s.pages) or any(p > pc + 1 for p in s.pages):
                problems.append(f"{q.id}: bad pages {s.pages} for {s.doc_key}")
        if q.type == "unanswerable" and not q.expect_abstain:
            problems.append(f"{q.id}: unanswerable item must set expect_abstain")
        if q.type not in ("unanswerable", "injection") and not q.expected_sources:
            problems.append(f"{q.id}: no expected_sources")
        if q.match == "numeric" and not isinstance(q.expected_answer, int | float):
            problems.append(f"{q.id}: numeric answer not a number")
        if q.match == "set" and not isinstance(q.expected_answer, list):
            problems.append(f"{q.id}: set answer not a list")
    # extraction ground truth
    for r in gt:
        if r["spec"].get("part_number") is None:
            problems.append(f"{r['doc_key']}: missing part_number")
        if "split" not in r or r["split"] not in ("dev", "test"):
            problems.append(f"{r['doc_key']}: bad split")
    real_path = dataset_dir / "extraction_real.jsonl"
    if real_path.exists():
        for r in read_jsonl(real_path):
            if r.get("verified_by_human") is not False:
                problems.append(f"{r['doc_key']}: real labels must be verified_by_human=false")
    scen = dataset_dir / "agent_scenarios.yaml"
    if scen.exists():
        data = yaml.safe_load(scen.read_text())
        ids2 = [s["id"] for s in data["scenarios"]]
        if len(ids2) < 14:
            problems.append(f"agent scenarios: {len(ids2)} < 14")
    return problems
