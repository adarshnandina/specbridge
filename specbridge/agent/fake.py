"""Deterministic FakeProvider responders for the agent (parse + compare)."""

from __future__ import annotations

import json
import re
from typing import Any

from specbridge.llm.base import LLMRequest
from specbridge.llm.fake_provider import FakeProvider

PN_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b")
IFACES = ["IO-Link", "PROFINET", "EtherCAT", "Modbus RTU", "CANopen"]


def parse_handler(req: LLMRequest) -> dict[str, Any]:
    text = req.messages[-1]["content"]
    m = PN_RE.search(text)
    constraints: list[dict[str, Any]] = []
    for i in IFACES:
        if re.search(i.replace("-", "[- ]?").replace(" ", r"[\s-]?"), text, flags=re.I):
            constraints.append({"field": "interfaces", "op": "contains", "value": i})
    ip = re.search(r"\bIP\s?([0-6][0-9]K?)\b", text, flags=re.I)
    if ip:
        constraints.append({"field": "ip_rating", "op": "gte", "value": "IP" + ip.group(1).upper()})
    return {"part_number": m.group(0) if m else "", "constraints": constraints}


def compare_handler(req: LLMRequest) -> dict[str, Any]:
    first = req.messages[0]["content"]
    cands = json.loads(first.split("<candidates>\n")[1].split("\n</candidates>")[0])
    last = req.messages[-1]["content"]
    if not (isinstance(last, list) and any(b.get("type") == "tool_result" for b in last)):
        top = [c["part_number"] for c in cands[:3]]
        return {
            "text": "",
            "tool_calls": [
                {
                    "name": "retrieve_evidence",
                    "id": f"toolu_e{i}",
                    "input": {
                        "part_number": pn,
                        "query": "operating temperature supply voltage protection",
                    },
                }
                for i, pn in enumerate(top)
            ],
        }
    ranking = []
    for block in last:
        if block.get("is_error") or not str(block.get("tool_use_id", "")).startswith("toolu_e"):
            continue
        idx = int(block["tool_use_id"].replace("toolu_e", ""))
        pn = cands[idx]["part_number"]
        m = re.search(r'<source chunk_id="([^"]+)"[^>]*>\n(.*?)\n</source>', block["content"], re.S)
        if not m:
            continue
        line = next(
            (ln for ln in m.group(2).split("\n") if re.search(r"\d", ln) and len(ln) > 8),
            m.group(2).split("\n")[0],
        )
        ranking.append(
            {
                "part_number": pn,
                "claims": [
                    {
                        "text": f"{pn} datasheet states: {line.strip(' |')}",
                        "citations": [{"chunk_id": m.group(1), "quote": line}],
                    }
                ],
            }
        )
    return {
        "text": "",
        "tool_calls": [{"name": "submit_ranking", "id": "toolu_s", "input": {"ranking": ranking}}],
    }


def register_agent_handlers(fake: FakeProvider) -> FakeProvider:
    fake.register("agent_parse", parse_handler)
    fake.register("agent_compare", compare_handler)
    return fake
