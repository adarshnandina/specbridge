"""PDF parsing with PyMuPDF: text blocks with bboxes, tables, headings, document metadata."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import pymupdf

KNOWN_VENDORS = {
    "nordwerk": "Nordwerk Sensorik",
    "kestrel": "Kestrel Drives",
    "alpenlicht": "Alpenlicht Automation",
}
VENDOR_PN = [
    re.compile(r"\bNS-[A-Z]{3}-\d{4}\b"),
    re.compile(r"\bKD-\d{3}\b"),
    re.compile(r"\bAL-[A-Z]{3}-\d{3}\b"),
]
GENERIC_PN = re.compile(r"\b[A-Z][A-Z0-9]{1,5}(?:-[A-Z0-9Ö]{2,}){1,3}\b")
REV_RE = re.compile(r"(?<!IO-Link )\b(?:Revision|Rev\.)\s*(\d+(?:\.\d+)*)")
FOOTER_FRACTION = 0.93


@dataclass
class Block:
    page_no: int
    bbox: tuple[float, float, float, float]
    text: str
    kind: str = "text"  # text | table
    is_heading: bool = False
    size: float = 0.0
    table_header: str | None = None


@dataclass
class ParsedPage:
    page_no: int
    width: float
    height: float
    text: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    vendor: str | None
    title: str | None
    part_numbers: list[str]
    revision: str | None
    tables_found: int

    @property
    def blocks(self) -> list[Block]:
        return [b for p in self.pages for b in p.blocks]


def _overlap_frac(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    area = (a[2] - a[0]) * (a[3] - a[1]) or 1.0
    return float((x1 - x0) * (y1 - y0) / area)


def table_to_markdown(rows: list[list[str | None]]) -> str:
    clean = [[" ".join((c or "").split()) for c in r] for r in rows if any(c for c in r)]
    if not clean:
        return ""
    width = max(len(r) for r in clean)
    clean = [r + [""] * (width - len(r)) for r in clean]
    lines = ["| " + " | ".join(clean[0]) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(r) + " |" for r in clean[1:]]
    return "\n".join(lines)


def _table_rows(page: Any, table: Any) -> list[list[str | None]]:
    """Cell text via the page text layer inside each cell bbox (keeps word spacing)."""
    rows: list[list[str | None]] = []
    rect: Any = pymupdf.Rect
    try:
        for row in table.rows:
            rows.append(
                [" ".join(page.get_textbox(rect(c)).split()) if c else None for c in row.cells]
            )
        return rows
    except Exception:
        return list(table.extract())


def _block_info(blk: dict) -> tuple[str, float, bool, int]:  # type: ignore[type-arg]
    texts, max_size, all_bold, nlines = [], 0.0, True, 0
    for line in blk.get("lines", []):
        nlines += 1
        parts = []
        for sp in line["spans"]:
            t = sp["text"]
            if not t.strip():
                parts.append(t)
                continue
            parts.append(t)
            max_size = max(max_size, sp["size"])
            if not ("bold" in sp["font"].lower() or sp["flags"] & 16):
                all_bold = False
        texts.append("".join(parts).strip())
    return " ".join(t for t in texts if t), max_size, all_bold, nlines


def parse_pdf(path: str | bytes) -> ParsedDocument:
    opener: Any = pymupdf.open
    doc: Any = opener(stream=path, filetype="pdf") if isinstance(path, bytes) else opener(path)
    size_chars: Counter[float] = Counter()
    tables_found = 0
    pages: list[ParsedPage] = []
    for page in doc:
        d = page.get_text("dict")
        try:
            tables = page.find_tables().tables
        except Exception:  # find_tables can fail on odd pages; degrade to text only
            tables = []
        tbboxes = [tuple(t.bbox) for t in tables]
        blocks: list[Block] = []
        for blk in d["blocks"]:
            if blk.get("type") != 0:
                continue
            text, size, all_bold, nlines = _block_info(blk)
            if not text:
                continue
            bbox = tuple(blk["bbox"])
            if any(_overlap_frac(bbox, tb) > 0.5 for tb in tbboxes):
                continue
            if bbox[1] > FOOTER_FRACTION * page.rect.height:
                continue  # running footer
            size_chars[round(size, 1)] += len(text)
            b = Block(page.number + 1, bbox, text, "text", False, size)
            b.table_header = "bold" if all_bold else None  # temp marker, cleared below
            blocks.append(b)
        for t, tb in zip(tables, tbboxes, strict=True):
            md = table_to_markdown(_table_rows(page, t))
            if md:
                tables_found += 1
                first = md.split("\n", 1)[0]
                blocks.append(Block(page.number + 1, tb, md, "table", False, 0.0, first))
        pages.append(
            ParsedPage(
                page.number + 1, page.rect.width, page.rect.height, page.get_text("text"), blocks
            )
        )
    body = size_chars.most_common(1)[0][0] if size_chars else 10.0
    for p in pages:
        for b in p.blocks:
            if b.kind != "text":
                continue
            bold = b.table_header == "bold"
            b.table_header = None
            short = len(b.text) <= 90 and not b.text.rstrip().endswith((".", ":"))
            b.is_heading = bool(short and (b.size >= body + 1.5 or (bold and b.size >= body)))
        # reading order: stream order for text, tables inserted by vertical position
        texts = [b for b in p.blocks if b.kind == "text"]
        tabs = sorted((b for b in p.blocks if b.kind == "table"), key=lambda b: b.bbox[1])
        merged: list[Block] = []
        ti = 0
        for b in texts:
            while ti < len(tabs) and tabs[ti].bbox[1] <= b.bbox[1]:
                merged.append(tabs[ti])
                ti += 1
            merged.append(b)
        merged.extend(tabs[ti:])
        p.blocks = merged
    full_text = "\n".join(p.text for p in pages)
    first_text_blocks = pages[0].blocks if pages else []
    title = None
    cands = [b for b in first_text_blocks if b.kind == "text" and b.size]
    if cands:
        title = max(cands, key=lambda b: b.size).text
    return ParsedDocument(
        pages=pages,
        vendor=detect_vendor(full_text),
        title=title,
        part_numbers=detect_part_numbers(full_text, title),
        revision=detect_revision(full_text),
        tables_found=tables_found,
    )


def detect_vendor(text: str) -> str | None:
    low = text.lower()
    for key, name in KNOWN_VENDORS.items():
        if key in low:
            return name
    return None


def detect_part_numbers(text: str, title: str | None = None, limit: int = 4) -> list[str]:
    counts: Counter[str] = Counter()
    for rx in VENDOR_PN:
        for m in rx.findall(text):
            counts[m] += 3
    for m in GENERIC_PN.findall(text):
        if not re.fullmatch(r"(?:IP|EN|IEC|DIN|ISO|UL|CE)[-0-9]*", m) and not m.startswith(
            ("EN-", "IEC-", "ISO-", "RS-", "TS-", "AWG")
        ):
            counts[m] += 1
    if title:
        for m in GENERIC_PN.findall(title):
            counts[m] += 5
    return [pn for pn, c in counts.most_common() if c >= 2][:limit]


def detect_revision(text: str) -> str | None:
    m = REV_RE.search(text)
    return m.group(1) if m else None
