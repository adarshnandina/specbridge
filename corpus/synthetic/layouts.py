"""Renders PartPlan -> PDF in four layout families and records the evidence page per field."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from corpus.synthetic.vendors import PartPlan

CATEGORY_LABEL = {
    "sensor": "Sensor",
    "drive": "Drive",
    "io_module": "I/O module",
    "power_supply": "Power supply",
}
CERT_VARIANTS = {
    "UL": ["UL", "UL Listed"],
    "cULus": ["cULus", "c-UL-us"],
    "RoHS": ["RoHS", "RoHS compliant"],
    "CE": ["CE"],
    "UKCA": ["UKCA"],
}
IFACE_VARIANTS = {
    "IO-Link": ["IO-Link", "IO Link"],
    "PROFINET": ["PROFINET", "PROFINET IO"],
    "EtherCAT": ["EtherCAT"],
    "Modbus RTU": ["Modbus RTU", "Modbus-RTU"],
    "CANopen": ["CANopen"],
    "4-20 mA": ["4–20 mA", "4...20 mA", "4-20 mA"],
}
VOLT_LABELS = ["Supply voltage", "Operating voltage", "Rated voltage"]
TEMP_LABELS = ["Operating temperature", "Ambient temperature", "Temperature range"]
IP_LABELS = ["Protection class", "Degree of protection", "Ingress protection"]
CUR_LABELS = ["Rated current", "Nominal current", "Current rating"]
PWR_LABELS = ["Power consumption", "Rated power", "Power rating"]

VENDOR_COLORS = {
    "nordwerk": colors.HexColor("#1f4e79"),
    "kestrel": colors.HexColor("#8a1c1c"),
    "alpenlicht": colors.HexColor("#2e6b3a"),
}


@dataclass
class Row:
    label: str
    value: str
    fields: tuple[str, ...]
    page: int = 1


class Fmt:
    def __init__(self, rng: random.Random, comma: bool) -> None:
        self.rng, self.comma = rng, comma

    def num(self, x: float) -> str:
        s = str(int(x)) if float(x).is_integer() else f"{x:g}"
        return s.replace(".", ",") if self.comma else s

    def temp(self, lo: float, hi: float, header_unit: bool = False) -> str:
        n = self.num
        hi_s = f"+{n(hi)}"
        lo_s = f"-{n(abs(lo))}" if lo < 0 else n(lo)
        if lo >= 0:
            hi_s = n(hi)
        if header_unit:
            return self.rng.choice([f"{lo_s}…{hi_s}", f"{lo_s}...{hi_s}", f"{lo_s} to {hi_s}"])
        c = self.rng.randrange(5)
        if c == 0:
            return f"{lo_s} °C … {hi_s} °C"
        if c == 1:
            lo_en = f"–{n(abs(lo))}" if lo < 0 else n(lo)
            return f"{lo_en} to {n(hi)} °C"
        if c == 2:
            return f"{lo_s}...{hi_s} °C"
        if c == 3:
            return f"{lo_s} °C to {hi_s} °C"
        return f"{lo_s}…{hi_s} °C"

    def volt(self, lo: float, hi: float, kind: str, header_unit: bool = False) -> str:
        n = self.num
        if header_unit:
            return self.rng.choice(
                [f"{n(lo)}…{n(hi)}", f"{n(lo)}...{n(hi)}", f"{n(lo)} to {n(hi)}"]
            )
        c = self.rng.randrange(5)
        nom = None
        for cand in (24, 230, 400, 48, 12):
            if lo <= cand <= hi:
                nom = cand
                break
        if c == 0 and nom is not None:
            return f"{nom} V {kind} ({n(lo)}–{n(hi)} V)"
        if c == 1:
            return f"{n(lo)}…{n(hi)} V {kind}"
        if c == 2:
            return f"{n(lo)} to {n(hi)} V {kind}"
        if c == 3:
            return f"{n(lo)}...{n(hi)} V"
        return f"{n(lo)}-{n(hi)} V {kind}"

    def ip(self, ip: str) -> str:
        if self.rng.random() < 0.4:
            return f"IP {ip[2:]}"
        return ip

    def current(self, a: float, allow_ma: bool = True) -> str:
        if allow_ma and a < 1 and self.rng.random() < 0.35:
            return f"{self.num(round(a * 1000, 3))} mA"
        return f"{self.num(a)} A"

    def power(self, w: float, drive: bool) -> str:
        if drive and w >= 1000 and self.rng.random() < 0.5:
            return f"{self.num(w / 1000)} kW"
        return f"{self.num(w)} W"

    def weight(self, g: float) -> str:
        if g >= 1000 and self.rng.random() < 0.5:
            return f"{self.num(g / 1000)} kg"
        return f"{self.num(g)} g"

    def dims(self, d: list[float]) -> str:
        sep = self.rng.choice([" × ", " x "])
        return sep.join(self.num(x) for x in d) + " mm"


def build_rows(plan: PartPlan, rng: random.Random, layout: str) -> list[Row]:
    sp = plan.full_spec()
    f = Fmt(rng, plan.vendor.decimal_comma)
    hdr = layout == "d"
    ac = plan.family.key in ("srv", "inv", "psu")
    kind = "AC" if ac else "DC"
    rows: list[Row] = [Row("Product group", CATEGORY_LABEL[sp["category"]], ("category",))]
    if sp.get("supply_voltage_min_v") is not None:
        label = rng.choice(VOLT_LABELS) + (f" [V {kind}]" if hdr else "")
        rows.append(
            Row(
                label,
                f.volt(sp["supply_voltage_min_v"], sp["supply_voltage_max_v"], kind, hdr),
                ("supply_voltage_min_v", "supply_voltage_max_v"),
            )
        )
    if sp.get("rated_current_a") is not None:
        label = rng.choice(CUR_LABELS) + (" [A]" if hdr else "")
        val = f.num(sp["rated_current_a"]) if hdr else f.current(sp["rated_current_a"])
        rows.append(Row(label, val, ("rated_current_a",)))
    if sp.get("power_w") is not None:
        label = rng.choice(PWR_LABELS) + (" [W]" if hdr else "")
        val = (
            f.num(sp["power_w"]) if hdr else f.power(sp["power_w"], plan.family.category == "drive")
        )
        rows.append(Row(label, val, ("power_w",)))
    if sp.get("operating_temp_min_c") is not None:
        label = rng.choice(TEMP_LABELS) + (" [°C]" if hdr else "")
        rows.append(
            Row(
                label,
                f.temp(sp["operating_temp_min_c"], sp["operating_temp_max_c"], hdr),
                ("operating_temp_min_c", "operating_temp_max_c"),
            )
        )
    if sp.get("ip_rating"):
        rows.append(Row(rng.choice(IP_LABELS), f.ip(sp["ip_rating"]), ("ip_rating",)))
    if sp.get("dimensions_mm"):
        label = "Dimensions (W × H × D)" + (" [mm]" if hdr else "")
        val = (
            " × ".join(f.num(x) for x in sp["dimensions_mm"])
            if hdr
            else f.dims(sp["dimensions_mm"])
        )
        rows.append(Row(label, val, ("dimensions_mm",)))
    if sp.get("weight_g") is not None:
        label = "Weight" + (" [g]" if hdr else "")
        val = f.num(sp["weight_g"]) if hdr else f.weight(sp["weight_g"])
        rows.append(Row(label, val, ("weight_g",)))
    if sp.get("interfaces"):
        vals = [rng.choice(IFACE_VARIANTS[i]) for i in sp["interfaces"]]
        rows.append(
            Row("Interface" if len(vals) == 1 else "Interfaces", ", ".join(vals), ("interfaces",))
        )
    if sp.get("certifications"):
        vals = [rng.choice(CERT_VARIANTS[c]) for c in sp["certifications"]]
        rows.append(Row("Approvals", ", ".join(vals), ("certifications",)))
    return rows


DESCRIPTIONS = {
    "ind": "Robust inductive proximity sensor for contactless detection of metallic objects in harsh industrial environments.",
    "pho": "Photoelectric sensor for reliable object detection with high switching frequency and easy alignment.",
    "prs": "Pressure transmitter with stainless steel sensing element for hydraulic and pneumatic applications.",
    "stp": "Compact stepper drive for precise positioning in packaging and handling machines.",
    "srv": "High-performance servo drive for dynamic multi-axis motion control.",
    "inv": "Frequency inverter for speed control of three-phase asynchronous motors in conveyors and pumps.",
    "dio": "Digital input/output module for decentralised signal acquisition in the control cabinet or on the machine.",
    "aio": "Analog input/output module with high resolution for process values such as pressure and temperature.",
    "psu": "DIN-rail power supply with high efficiency and wide input range for industrial control cabinets.",
}
NOTES = (
    "Installation: Mount according to the installation instructions supplied with the product. "
    "Observe the local electrical regulations. Technical data are valid at the stated "
    "ambient conditions unless noted otherwise."
)


def _styles() -> dict[str, ParagraphStyle]:
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "t",
            parent=ss["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            alignment=0,
            spaceAfter=4,
        ),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12),
        "body": ParagraphStyle(
            "b", parent=ss["BodyText"], fontName="Helvetica", fontSize=10, leading=13
        ),
        "cell": ParagraphStyle(
            "c", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=12
        ),
        "cellb": ParagraphStyle(
            "cb", parent=ss["BodyText"], fontName="Helvetica-Bold", fontSize=9.5, leading=12
        ),
        "small": ParagraphStyle(
            "s",
            parent=ss["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#444444"),
        ),
    }


def _footer_factory(plan: PartPlan):  # type: ignore[no-untyped-def]
    def footer(canvas, doc):  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(
            20 * mm,
            12 * mm,
            f"{plan.vendor.name} · {plan.part_number} · Revision {plan.revision} · "
            "Subject to technical change without notice.",
        )
        canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return footer


def _header_flowables(plan: PartPlan, st: dict[str, ParagraphStyle]) -> list[Any]:
    color = VENDOR_COLORS[plan.vendor.slug]
    band = Table(
        [[Paragraph(f'<font color="white"><b>{escape(plan.vendor.name)}</b></font>', st["body"])]],
        colWidths=[170 * mm],
    )
    band.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return [
        band,
        Spacer(1, 6),
        Paragraph(escape(f"{plan.product_name}"), st["title"]),
        Paragraph(
            f"Part number: <b>{escape(plan.part_number)}</b> &nbsp;|&nbsp; "
            f"Revision {escape(plan.revision)}",
            st["body"],
        ),
        Spacer(1, 6),
    ]


def _grid(rows: list[list[Any]], widths: list[float], header: bool = False) -> Table:
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef1f5")),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d5dbe3"))]
    t.setStyle(TableStyle(style))
    return t


def render_pdf(plan: PartPlan, path: Path, seed_rng: random.Random) -> dict[str, int]:
    """Render the datasheet. Returns {field: page} for evidence locations."""
    rng = random.Random(seed_rng.random())
    layout = plan.layout
    st = _styles()
    rows = build_rows(plan, rng, layout)
    path.parent.mkdir(parents=True, exist_ok=True)
    footer = _footer_factory(plan)
    desc = Paragraph(escape(DESCRIPTIONS[plan.family.key]), st["body"])
    notes = [Paragraph("Notes", st["h2"]), Paragraph(escape(NOTES), st["body"])]
    if plan.notes:
        notes.append(Spacer(1, 4))
        notes.append(Paragraph(escape(plan.notes), st["body"]))
    pages: dict[str, int] = {
        f: 1 for f in ("part_number", "manufacturer", "product_name", "datasheet_revision")
    }
    story: list[Any] = _header_flowables(plan, st)

    def cells(rs: list[Row]) -> list[list[Any]]:
        return [
            [Paragraph(escape(r.label), st["cellb"]), Paragraph(escape(r.value), st["cell"])]
            for r in rs
        ]

    if layout in ("a", "d"):
        story += [desc, Spacer(1, 8), Paragraph("Technical data", st["h2"])]
        data = cells(rows)
        if layout == "d":
            data = [
                [
                    Paragraph("<b>Parameter [unit]</b>", st["cell"]),
                    Paragraph("<b>Value</b>", st["cell"]),
                ],
                *data,
            ]
        story.append(_grid(data, [75 * mm, 95 * mm], header=layout == "d"))
        story += [Spacer(1, 10), *notes]
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=18 * mm,
            bottomMargin=20 * mm,
            invariant=1,
            title=plan.product_name,
            author=plan.vendor.name,
        )
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        for r in rows:
            for f in r.fields:
                pages[f] = 1
    elif layout == "b":
        head = [
            *_header_flowables(plan, st),
            desc,
            Spacer(1, 8),
            Paragraph("Technical data", st["h2"]),
        ]
        half = (len(rows) + 1) // 2
        flow = [
            *head,
            FrameBreak(),
            *_kv(rows[:half], st),
            FrameBreak(),
            *_kv(rows[half:], st),
            FrameBreak(),
            *notes,
        ]
        doc_b = BaseDocTemplate(
            str(path), pagesize=A4, invariant=1, title=plan.product_name, author=plan.vendor.name
        )
        w, h = A4
        colw = (w - 40 * mm - 8 * mm) / 2
        top = Frame(20 * mm, h - 100 * mm, w - 40 * mm, 82 * mm, id="top")
        left = Frame(20 * mm, h - 190 * mm, colw, 88 * mm, id="l")
        right = Frame(20 * mm + colw + 8 * mm, h - 190 * mm, colw, 88 * mm, id="r")
        bottom = Frame(20 * mm, 20 * mm, w - 40 * mm, h - 215 * mm, id="bot")
        doc_b.addPageTemplates(
            [PageTemplate(id="p", frames=[top, left, right, bottom], onPage=footer)]
        )
        doc_b.build(flow)
        for r in rows:
            for f in r.fields:
                pages[f] = 1
    elif layout == "c":
        feature_rows = [r for r in rows if r.fields[0] in ("interfaces", "certifications")]
        table_rows = [r for r in rows if r not in feature_rows]
        story += [desc, Spacer(1, 8), Paragraph("Features", st["h2"])]
        story.append(
            Paragraph(
                f"• {escape(CATEGORY_LABEL[plan.family.category])} for industrial "
                "automation applications",
                st["body"],
            )
        )
        for r in feature_rows:
            story.append(Paragraph(f"• {escape(r.label)}: {escape(r.value)}", st["body"]))
        story += [
            Spacer(1, 6),
            Paragraph("Technical data on the following page.", st["small"]),
            PageBreak(),
        ]
        story.append(Paragraph(f"{escape(plan.product_name)} — Technical data", st["h2"]))
        foot_idx: list[str] = []
        data = []
        for r in table_rows:
            label = r.label
            if r.fields[0] == "rated_current_a":
                label += "¹"
                foot_idx.append("¹ At 25 °C ambient temperature.")
            elif r.fields[0] == "power_w":
                label += "²"
                foot_idx.append("² Typical value at nominal load.")
            data.append(
                [Paragraph(escape(label), st["cellb"]), Paragraph(escape(r.value), st["cell"])]
            )
        story.append(_grid(data, [75 * mm, 95 * mm]))
        story.append(Spacer(1, 6))
        for ft in foot_idx:
            story.append(Paragraph(escape(ft), st["small"]))
        story += [Spacer(1, 10), *notes]
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=18 * mm,
            bottomMargin=20 * mm,
            invariant=1,
            title=plan.product_name,
            author=plan.vendor.name,
        )
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        for r in feature_rows:
            for f in r.fields:
                pages[f] = 1
        for r in table_rows:
            for f in r.fields:
                pages[f] = 2
        pages["category"] = 2 if any(r.fields == ("category",) for r in table_rows) else 1
    else:
        raise ValueError(layout)
    return pages


def _kv(rows: list[Row], st: dict[str, ParagraphStyle]) -> list[Any]:
    out: list[Any] = []
    for r in rows:
        out.append(Paragraph(f"<b>{escape(r.label)}:</b> {escape(r.value)}", st["body"]))
        out.append(Spacer(1, 4))
    return out
