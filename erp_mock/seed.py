"""Seed the mock ERP from the synthetic ground truth.  python -m erp_mock.seed"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from corpus.synthetic.ground_truth import GT_PATH, load_ground_truth
from erp_mock.app import SCHEMA


def seed(db_path: str, gt_path: Path | str = GT_PATH) -> int:
    records = [r for r in load_ground_truth(gt_path) if r["is_latest"]]
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db_path)
    c.executescript(SCHEMA)
    for r in records:
        spec: dict[str, Any] = r["spec"]
        c.execute(
            "INSERT OR REPLACE INTO parts VALUES (?,?,?,?,?)",
            (r["part_number"], r["category"], r["lifecycle_status"], json.dumps(spec), time.time()),
        )
    c.commit()
    c.close()
    return len(records)


if __name__ == "__main__":
    path = os.environ.get("ERP_DB_PATH", "data/erp.sqlite")
    print(f"seeded {seed(path)} parts into {path}")
