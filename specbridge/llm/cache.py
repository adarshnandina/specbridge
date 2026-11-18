"""On-disk SQLite response cache for eval re-runs."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from specbridge.llm.base import LLMRequest, LLMResult, ToolCall


def cache_key(provider: str, req: LLMRequest) -> str:
    blob = json.dumps(
        [provider, req.model, req.system, req.messages, req.tools, req.temperature],
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(blob.encode()).hexdigest()


class ResponseCache:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT NOT NULL)")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def get(self, key: str) -> LLMResult | None:
        with self._conn() as c:
            row = c.execute("SELECT v FROM cache WHERE k=?", (key,)).fetchone()
        if not row:
            return None
        d = json.loads(row[0])
        d["tool_calls"] = [ToolCall(**t) for t in d["tool_calls"]]
        return LLMResult(**d)

    def put(self, key: str, res: LLMResult) -> None:
        d = {
            "text": res.text,
            "tool_calls": [{"name": t.name, "input": t.input, "id": t.id} for t in res.tool_calls],
            "input_tokens": res.input_tokens,
            "output_tokens": res.output_tokens,
            "model": res.model,
            "latency_ms": res.latency_ms,
            "provider": res.provider,
            "cache_hit": False,
        }
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO cache VALUES (?,?)", (key, json.dumps(d)))
