"""LLM judge for open questions (usefulness 1-3). Uncalibrated until judge_calibration is scored."""

from __future__ import annotations

from pydantic import BaseModel, Field

from specbridge.llm.usage import LLMService
from specbridge.prompts import load_prompt


class JudgeScore(BaseModel):
    score: int = Field(ge=1, le=3)
    rationale: str = ""


def judge_answer(llm: LLMService, question: str, reference: str, candidate: str) -> int:
    prompt = load_prompt("judge_usefulness", 1)
    msg = f"QUESTION: {question}\n\nREFERENCE: {reference}\n\nCANDIDATE: {candidate}"
    out = llm.structured(
        JudgeScore,
        tool_name="submit_score",
        tool_description="Submit the 1-3 usefulness score.",
        system=prompt.text,
        messages=[{"role": "user", "content": msg}],
        purpose="judge",
        prompt_version=prompt.label,
        max_tokens=300,
    )
    return out.score
