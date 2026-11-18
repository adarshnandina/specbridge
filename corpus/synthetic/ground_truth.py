"""Ground-truth records for the synthetic corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GT_PATH = Path("eval/datasets/extraction_synthetic.jsonl")


def make_splits(part_numbers: list[str]) -> dict[str, str]:
    """Deterministic 60/40 dev/test split by sorted part number (revisions share a split)."""
    return {
        pn: ("test" if i % 5 in (1, 3) else "dev") for i, pn in enumerate(sorted(set(part_numbers)))
    }


def load_ground_truth(path: Path | str = GT_PATH) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_ground_truth(records: list[dict[str, Any]], path: Path | str = GT_PATH) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in sorted(records, key=lambda r: r["doc_key"]):
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def latest_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in records if r["is_latest"]]
