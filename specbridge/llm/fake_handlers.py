"""Deterministic offline responders for the FakeProvider (pipeline checks only).

The QA responder is a crude extractive baseline: it is NOT a quality benchmark for answering.
"""

from __future__ import annotations

import re
from typing import Any

from specbridge.llm.base import LLMRequest
from specbridge.llm.fake_provider import FakeProvider
from specbridge.retrieval.keyword import STOPWORDS

SOURCE_RE = re.compile(r'<source id="(S\d+)" doc="([^"]*)" page="(\d+)">\n(.*?)\n</source>', re.S)
KEYWORDS = {
    "temperature": ("temperature", "°c"),
    "voltage": ("voltage", " v"),
    "weight": ("weight",),
    "current": ("current",),
    "power": ("power",),
    "dimension": ("dimension",),
    "ip": ("protection", "ip "),
    "interface": ("interface",),
    "certif": ("approval",),
    "approval": ("approval",),
    "protection": ("protection",),
    "revision": ("revision",),
}


def qa_handler(req: LLMRequest) -> dict[str, Any]:
    text = req.messages[-1]["content"]
    question = text.rsplit("Question:", 1)[-1].strip()
    sources = SOURCE_RE.findall(text)
    qwords = {w.lower() for w in re.findall(r"[A-Za-z0-9\-]+", question)} - STOPWORDS
    pns = [w for w in re.findall(r"[A-Z][A-Z0-9]*-[A-Z0-9-]+", question)]
    wanted = [k for key, ks in KEYWORDS.items() if key in question.lower() for k in ks]
    best: tuple[int, str, str] | None = None
    for sid, doc, _page, body in sources:
        if pns and not any(pn in doc or pn in body for pn in pns):
            continue
        for line in body.split("\n"):
            low = line.lower()
            score = sum(w in low for w in qwords) + 3 * sum(k in low for k in wanted)
            if wanted and not any(k in low for k in wanted):
                continue
            if best is None or score > best[0]:
                best = (score, sid, line.strip(" |"))
    if best is None or best[0] < 3 or not pns and not wanted:
        return {
            "answerable": False,
            "answer": "The documents do not contain this information.",
            "citations": [],
        }
    _, sid, line = best
    return {"answerable": True, "answer": line, "citations": [{"source_id": sid, "quote": line}]}


def register_default_handlers(fake: FakeProvider) -> FakeProvider:
    fake.register("qa", qa_handler)
    return fake
