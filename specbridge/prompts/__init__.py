"""Versioned prompt files: specbridge/prompts/<name>.v<N>.md with front matter."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

PROMPT_DIR = Path(__file__).parent


@dataclass(frozen=True)
class Prompt:
    name: str
    version: int
    purpose: str
    text: str

    @property
    def label(self) -> str:
        return f"{self.name}.v{self.version}"


@lru_cache
def load_prompt(name: str, version: int) -> Prompt:
    path = PROMPT_DIR / f"{name}.v{version}.md"
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise ValueError(f"{path.name}: missing front matter")
    _, fm, body = raw.split("---", 2)
    meta = yaml.safe_load(fm)
    if meta["name"] != name or int(meta["version"]) != version:
        raise ValueError(f"{path.name}: front matter does not match file name")
    return Prompt(name, version, meta["purpose"], body.strip())
