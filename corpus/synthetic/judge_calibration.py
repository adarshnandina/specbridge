"""Build eval/datasets/judge_calibration.jsonl: 20 open-question answers for a human to score 1-3.

Candidate answers are PROGRAMMATIC (one faithful, one with a wrong value per question), not model
output, so a human can calibrate the judge against known-good and known-bad answers. The
`human_score` field is intentionally empty: filling it in is a task for the project owner.
"""

from __future__ import annotations

import json
from pathlib import Path

from specbridge.eval.datasets import load_qa

OUT = Path("eval/datasets/judge_calibration.jsonl")


def build() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for q in [x for x in load_qa() if x.type == "open"]:
        ref = str(q.expected_answer)
        good = ref
        bad = ref.replace("protection IP", "protection IP6").replace(
            "operating temperature", "operating temperature (max)"
        )
        # a clearly wrong variant: shift the first number in the supply-voltage clause
        import re

        nums = re.findall(r"Supply voltage ([\d.]+)-([\d.]+) V", ref)
        if nums:
            lo, hi = nums[0]
            bad = ref.replace(f"{lo}-{hi} V", f"{float(lo) * 3:g}-{float(hi) * 3:g} V")
        for kind, ans in (("faithful", good), ("wrong_voltage", bad)):
            rows.append(
                {
                    "id": f"jc-{len(rows):03d}",
                    "question_id": q.id,
                    "question": q.question,
                    "reference_answer": ref,
                    "candidate_answer": ans,
                    "candidate_kind": kind,
                    "answer_source": "programmatic (not model output)",
                    "human_score": None,
                    "scoring_guide": "3 = correct and complete, 2 = partially correct/incomplete, "
                    "1 = wrong, misleading or empty",
                }
            )
    return rows


def main() -> None:
    rows = build()
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"wrote {len(rows)} items to {OUT}")


if __name__ == "__main__":
    main()
