"""Chunking strategies: 'fixed' (baseline) and 'layout' (headings + tables + context header)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from specbridge.ingestion.parser import Block, ParsedDocument


@dataclass
class ChunkOptions:
    strategy: str = "layout"
    context_header: bool = True
    target_tokens: int = 300
    overlap_tokens: int = 50
    max_layout_tokens: int = 400


@dataclass
class ChunkDraft:
    chunk_index: int
    chunk_type: str
    page_no: int
    content: str  # clean text for display/citation
    bboxes: list[list[float]]
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
    search_text: str | None = None  # text embedded + FTS-indexed (header + content)


def context_header(doc: ParsedDocument, section: str | None, doc_key: str | None = None) -> str:
    pns = ", ".join(doc.part_numbers) or (doc_key or "")
    parts = [
        doc.vendor or "",
        pns,
        doc.title or "",
        f"Rev {doc.revision}" if doc.revision else "",
        section or "",
    ]
    return "[" + " | ".join(p for p in parts if p) + "]"


def _finish(
    drafts: list[ChunkDraft],
    doc: ParsedDocument,
    opts: ChunkOptions,
    count: Callable[[str], int],
    doc_key: str | None,
) -> list[ChunkDraft]:
    for i, d in enumerate(drafts):
        d.chunk_index = i
        d.token_count = count(d.content)
        d.metadata.setdefault("part_numbers", doc.part_numbers)
        d.metadata.setdefault("revision", doc.revision)
        if opts.context_header and opts.strategy == "layout":
            hdr = context_header(doc, d.metadata.get("section"), doc_key)
            d.metadata["context_header"] = hdr
            d.search_text = f"{hdr}\n{d.content}"
        else:
            d.search_text = d.content
    return drafts


def chunk_layout(
    doc: ParsedDocument, opts: ChunkOptions, count: Callable[[str], int], doc_key: str | None = None
) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    section: str | None = None
    for page in doc.pages:
        buf: list[Block] = []
        sec_at_start = section

        def flush(sec: str | None, page_no: int = page.page_no) -> None:
            nonlocal buf
            if not buf:
                return
            texts: list[Block] = []
            for b in buf:
                texts.append(b)
                if sum(count(x.text) for x in texts) >= opts.max_layout_tokens:
                    drafts.append(_mk(texts, sec, page_no))
                    texts = []
            if texts:
                drafts.append(_mk(texts, sec, page_no))
            buf = []

        def _mk(bs: list[Block], sec: str | None, page_no: int) -> ChunkDraft:
            return ChunkDraft(
                0,
                "text",
                page_no,
                "\n".join(b.text for b in bs),
                [list(b.bbox) for b in bs],
                0,
                {"section": sec},
            )

        for b in page.blocks:
            if b.kind == "table":
                if all(x.is_heading for x in buf):
                    buf = []  # heading-only buffer: the heading is kept as the table's section
                flush(section)
                drafts.append(
                    ChunkDraft(
                        0,
                        "table",
                        page.page_no,
                        b.text,
                        [list(b.bbox)],
                        0,
                        {"section": section, "table_header": b.table_header},
                    )
                )
            elif b.is_heading:
                if any(not x.is_heading for x in buf):
                    flush(section)
                section = b.text
                buf.append(b)  # heading text stays with its section content
            else:
                buf.append(b)
        flush(section)
        _ = sec_at_start
    # drop chunks that are only a vendor banner / empty heading
    drafts = [d for d in drafts if len(d.content.strip()) > 3]
    return _finish(drafts, doc, opts, count, doc_key)


def chunk_fixed(
    doc: ParsedDocument, opts: ChunkOptions, count: Callable[[str], int], doc_key: str | None = None
) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    for page in doc.pages:
        blocks = sorted(page.blocks, key=lambda b: (round(b.bbox[1]), b.bbox[0]))
        words: list[tuple[str, int]] = []
        for bi, b in enumerate(blocks):
            for w in b.text.split():
                words.append((w, bi))
        if not words:
            continue
        wtok = [max(1, count(w)) for w, _ in words]
        start = 0
        while start < len(words):
            n, end = 0, start
            while end < len(words) and n + wtok[end] <= opts.target_tokens:
                n += wtok[end]
                end += 1
            end = max(end, start + 1)
            idx = sorted({bi for _, bi in words[start:end]})
            x0 = min(blocks[i].bbox[0] for i in idx)
            y0 = min(blocks[i].bbox[1] for i in idx)
            x1 = max(blocks[i].bbox[2] for i in idx)
            y1 = max(blocks[i].bbox[3] for i in idx)
            drafts.append(
                ChunkDraft(
                    0,
                    "text",
                    page.page_no,
                    " ".join(w for w, _ in words[start:end]),
                    [[x0, y0, x1, y1]],
                    0,
                    {},
                )
            )
            if end >= len(words):
                break
            back, m = end, 0
            while back > start + 1 and m + wtok[back - 1] <= opts.overlap_tokens:
                back -= 1
                m += wtok[back]
            start = max(back, start + 1)
    return _finish(drafts, doc, opts, count, doc_key)


def make_chunks(
    doc: ParsedDocument, opts: ChunkOptions, count: Callable[[str], int], doc_key: str | None = None
) -> list[ChunkDraft]:
    if opts.strategy == "layout":
        return chunk_layout(doc, opts, count, doc_key)
    if opts.strategy == "fixed":
        return chunk_fixed(doc, opts, count, doc_key)
    raise ValueError(f"unknown chunk strategy {opts.strategy!r}")
