"""Registers the extraction and agent suites once those modules exist."""

from __future__ import annotations

import importlib

for _mod in (
    "specbridge.extraction.eval_suite",
    "specbridge.agent.eval_suite",
    "specbridge.eval.calibration",
):
    try:
        importlib.import_module(_mod)
    except ModuleNotFoundError as exc:
        if not _mod.startswith(exc.name or "!"):  # a real missing dependency, re-raise
            raise
