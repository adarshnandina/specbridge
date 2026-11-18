"""Fictional vendors, product families and deterministic spec sampling."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from specbridge.extraction.fields import is_candidate_for


@dataclass(frozen=True)
class Family:
    key: str
    title: str
    category: str
    prefix: str  # part number prefix
    first_no: int
    step: int
    sampler: str


@dataclass(frozen=True)
class Vendor:
    slug: str
    name: str
    series: str
    decimal_comma: bool
    families: tuple[Family, ...]


VENDORS: tuple[Vendor, ...] = (
    Vendor(
        "nordwerk",
        "Nordwerk Sensorik",
        "NordSense",
        True,
        (
            Family("ind", "Inductive Proximity Sensor", "sensor", "NS-IND-", 1200, 4, "ind"),
            Family("pho", "Photoelectric Sensor", "sensor", "NS-PHO-", 2300, 6, "pho"),
            Family("prs", "Pressure Transmitter", "sensor", "NS-PRS-", 3400, 5, "prs"),
        ),
    ),
    Vendor(
        "kestrel",
        "Kestrel Drives",
        "KestrelMotion",
        False,
        (
            Family("stp", "Stepper Drive", "drive", "KD-", 110, 10, "stp"),
            Family("srv", "Servo Drive", "drive", "KD-", 210, 10, "srv"),
            Family("inv", "Frequency Inverter", "drive", "KD-", 310, 10, "inv"),
        ),
    ),
    Vendor(
        "alpenlicht",
        "Alpenlicht Automation",
        "AlpenIO",
        False,
        (
            Family("dio", "Digital I/O Module", "io_module", "AL-DIO-", 101, 2, "dio"),
            Family("aio", "Analog I/O Module", "io_module", "AL-AIO-", 201, 2, "aio"),
            Family("psu", "Power Supply", "power_supply", "AL-PSU-", 301, 3, "psu"),
        ),
    ),
)

CERT_POOL = ["CE", "UL", "cULus", "RoHS", "UKCA"]
SIZE_TAGS = ["M8", "M12", "M18", "M30", "Compact", "Slim", "Pro", "Basic", "Plus", "Mini"]


def _certs(rng: random.Random, must: tuple[str, ...] = ("CE",)) -> list[str]:
    extra = [c for c in CERT_POOL if c not in must]
    k = rng.randint(0, 3)
    chosen = set(must) | set(rng.sample(extra, k))
    return [c for c in CERT_POOL if c in chosen]


def _opt(rng: random.Random, value: Any, p_present: float) -> Any:
    return value if rng.random() < p_present else None


def sample_spec(fam: Family, rng: random.Random) -> dict[str, Any]:
    """Return normalized spec values (without identity fields)."""
    s = fam.sampler
    sp: dict[str, Any] = {}
    if s == "ind":
        sp["supply_voltage_min_v"], sp["supply_voltage_max_v"] = rng.choice(
            [(10, 30), (12, 30), (10, 36), (15, 30)]
        )
        sp["rated_current_a"] = rng.choice([0.1, 0.2, 0.25, 0.3, 0.4, 0.5])
        sp["power_w"] = _opt(rng, rng.choice([0.5, 0.8, 1.0, 1.5]), 0.3)
        sp["operating_temp_min_c"] = rng.choice([-25, -40])
        sp["operating_temp_max_c"] = rng.choice([70, 85, 100])
        sp["ip_rating"] = rng.choice(["IP67", "IP67", "IP68", "IP69K"])
        sp["interfaces"] = _opt(rng, ["IO-Link"], 0.5)
        sp["dimensions_mm"] = [
            rng.choice([8, 12, 18, 30]),
            rng.choice([8, 12, 18, 30]),
            rng.choice([40, 50, 60, 75]),
        ]
        sp["weight_g"] = _opt(rng, rng.choice([25, 40, 60, 95, 140]), 0.85)
    elif s == "pho":
        sp["supply_voltage_min_v"], sp["supply_voltage_max_v"] = rng.choice(
            [(10, 30), (18, 30), (10, 28), (12, 24)]
        )
        sp["rated_current_a"] = rng.choice([0.1, 0.15, 0.2])
        sp["power_w"] = _opt(rng, rng.choice([0.6, 1.2, 2.0]), 0.4)
        sp["operating_temp_min_c"] = rng.choice([-20, -25, -40])
        sp["operating_temp_max_c"] = rng.choice([55, 60, 70, 85])
        sp["ip_rating"] = rng.choice(["IP65", "IP67", "IP67", "IP69K"])
        sp["interfaces"] = _opt(rng, ["IO-Link"], 0.6)
        sp["dimensions_mm"] = [
            rng.choice([12, 15, 20]),
            rng.choice([30, 40, 50]),
            rng.choice([25, 35, 45]),
        ]
        sp["weight_g"] = _opt(rng, rng.choice([30, 55, 80, 120]), 0.8)
    elif s == "prs":
        sp["supply_voltage_min_v"], sp["supply_voltage_max_v"] = rng.choice(
            [(9, 32), (12, 30), (8, 33)]
        )
        sp["rated_current_a"] = 0.02
        sp["power_w"] = _opt(rng, rng.choice([0.5, 0.7]), 0.3)
        sp["operating_temp_min_c"] = rng.choice([-40, -30])
        sp["operating_temp_max_c"] = rng.choice([85, 105, 125])
        sp["ip_rating"] = rng.choice(["IP65", "IP67", "IP69K"])
        sp["interfaces"] = rng.choice([["4-20 mA"], ["4-20 mA"], ["4-20 mA", "IO-Link"]])
        sp["dimensions_mm"] = [
            rng.choice([24, 27, 30]),
            rng.choice([24, 27, 30]),
            rng.choice([55, 70, 85]),
        ]
        sp["weight_g"] = _opt(rng, rng.choice([80, 120, 180, 240]), 0.85)
    elif s == "stp":
        sp["supply_voltage_min_v"], sp["supply_voltage_max_v"] = rng.choice(
            [(18, 48), (24, 55), (20, 50)]
        )
        sp["rated_current_a"] = rng.choice([1.5, 2.8, 4.2, 6.0, 8.0])
        sp["power_w"] = rng.choice([60, 120, 200, 300, 400])
        sp["operating_temp_min_c"] = rng.choice([0, -10])
        sp["operating_temp_max_c"] = rng.choice([40, 50, 55])
        sp["ip_rating"] = rng.choice(["IP20", "IP20", "IP40"])
        sp["interfaces"] = rng.choice([["CANopen"], ["Modbus RTU"], ["CANopen", "Modbus RTU"]])
        sp["dimensions_mm"] = [
            rng.choice([42, 56, 60]),
            rng.choice([90, 110]),
            rng.choice([70, 85]),
        ]
        sp["weight_g"] = _opt(rng, rng.choice([280, 340, 450, 620]), 0.8)
    elif s == "srv":
        sp["supply_voltage_min_v"], sp["supply_voltage_max_v"] = rng.choice(
            [(200, 240), (380, 480), (200, 480)]
        )
        sp["rated_current_a"] = rng.choice([3.0, 5.0, 9.0, 16.0, 24.0])
        sp["power_w"] = rng.choice([750, 1500, 2200, 4000, 7500])
        sp["operating_temp_min_c"] = rng.choice([0, -10])
        sp["operating_temp_max_c"] = rng.choice([45, 50, 55])
        sp["ip_rating"] = rng.choice(["IP20", "IP20", "IP54", "IP65"])
        sp["interfaces"] = rng.choice(
            [
                ["EtherCAT"],
                ["EtherCAT", "CANopen"],
                ["PROFINET"],
                ["EtherCAT", "Modbus RTU"],
                ["CANopen"],
            ]
        )
        sp["dimensions_mm"] = [
            rng.choice([70, 90, 110]),
            rng.choice([180, 220, 260]),
            rng.choice([150, 190]),
        ]
        sp["weight_g"] = rng.choice([1800, 2600, 3900, 5200])
    elif s == "inv":
        sp["supply_voltage_min_v"], sp["supply_voltage_max_v"] = rng.choice(
            [(200, 240), (380, 480), (340, 520)]
        )
        sp["rated_current_a"] = rng.choice([2.4, 4.0, 7.5, 12.0, 25.0])
        sp["power_w"] = rng.choice([550, 1100, 2200, 4000, 11000])
        sp["operating_temp_min_c"] = rng.choice([-10, 0, -20])
        sp["operating_temp_max_c"] = rng.choice([40, 50, 60])
        sp["ip_rating"] = rng.choice(["IP20", "IP21", "IP54"])
        sp["interfaces"] = rng.choice(
            [["Modbus RTU"], ["PROFINET"], ["EtherCAT"], ["Modbus RTU", "CANopen"]]
        )
        sp["dimensions_mm"] = [
            rng.choice([90, 120, 150]),
            rng.choice([200, 250, 300]),
            rng.choice([160, 190]),
        ]
        sp["weight_g"] = _opt(rng, rng.choice([2100, 3300, 4800, 7200]), 0.9)
    elif s == "dio":
        sp["supply_voltage_min_v"], sp["supply_voltage_max_v"] = rng.choice(
            [(18, 30), (19.2, 28.8), (20, 30)]
        )
        sp["rated_current_a"] = rng.choice([0.2, 0.3, 0.5, 0.8])
        sp["power_w"] = rng.choice([2.0, 3.5, 5.0, 6.0])
        sp["operating_temp_min_c"] = rng.choice([-20, -40, 0])
        sp["operating_temp_max_c"] = rng.choice([60, 70, 85])
        sp["ip_rating"] = rng.choice(["IP20", "IP20", "IP65", "IP67"])
        sp["interfaces"] = rng.choice(
            [["PROFINET"], ["EtherCAT"], ["Modbus RTU"], ["IO-Link"], ["PROFINET", "IO-Link"]]
        )
        sp["dimensions_mm"] = [rng.choice([30, 45, 60]), 110, rng.choice([70, 90])]
        sp["weight_g"] = _opt(rng, rng.choice([110, 160, 240, 310]), 0.85)
    elif s == "aio":
        sp["supply_voltage_min_v"], sp["supply_voltage_max_v"] = rng.choice(
            [(18, 30), (20, 30), (19.2, 28.8)]
        )
        sp["rated_current_a"] = rng.choice([0.25, 0.4, 0.6])
        sp["power_w"] = rng.choice([3.0, 4.5, 6.5])
        sp["operating_temp_min_c"] = rng.choice([-20, -25, 0])
        sp["operating_temp_max_c"] = rng.choice([55, 60, 70])
        sp["ip_rating"] = rng.choice(["IP20", "IP20", "IP67"])
        sp["interfaces"] = rng.choice(
            [
                ["PROFINET", "4-20 mA"],
                ["EtherCAT", "4-20 mA"],
                ["Modbus RTU", "4-20 mA"],
                ["CANopen"],
            ]
        )
        sp["dimensions_mm"] = [rng.choice([30, 45]), 110, rng.choice([70, 90])]
        sp["weight_g"] = _opt(rng, rng.choice([120, 180, 260]), 0.8)
    elif s == "psu":
        sp["supply_voltage_min_v"], sp["supply_voltage_max_v"] = rng.choice(
            [(100, 240), (85, 264), (90, 264)]
        )
        sp["rated_current_a"] = rng.choice([2.5, 5.0, 10.0, 20.0, 40.0])
        sp["power_w"] = None
        sp["operating_temp_min_c"] = rng.choice([-25, -40, -10])
        sp["operating_temp_max_c"] = rng.choice([60, 70, 75])
        sp["ip_rating"] = rng.choice(["IP20", "IP20", "IP65"])
        sp["interfaces"] = _opt(rng, ["Modbus RTU"], 0.2)
        sp["dimensions_mm"] = [rng.choice([32, 48, 65, 90]), 124, rng.choice([102, 117])]
        sp["weight_g"] = _opt(rng, rng.choice([280, 450, 680, 1100]), 0.85)
        sp["power_w"] = round(sp["rated_current_a"] * 24)
    else:
        raise ValueError(s)
    sp["certifications"] = _certs(rng)
    return sp


@dataclass
class PartPlan:
    vendor: Vendor
    family: Family
    index: int
    part_number: str
    product_name: str
    spec: dict[str, Any]
    revision: str = "1.0"
    layout: str = "a"
    lifecycle: str = "active"
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def doc_key(self) -> str:
        return f"{self.vendor.slug}/{self.part_number}/rev{self.revision}"

    def full_spec(self) -> dict[str, Any]:
        sp = dict(self.spec)
        sp.update(
            part_number=self.part_number,
            manufacturer=self.vendor.name,
            product_name=self.product_name,
            category=self.family.category,
            datasheet_revision=self.revision,
        )
        for k in ("power_w", "weight_g", "interfaces", "dimensions_mm"):
            sp.setdefault(k, None)
        return sp


def build_parts(seed: int = 42) -> list[PartPlan]:
    rng = random.Random(seed)
    parts: list[PartPlan] = []
    for vendor in VENDORS:
        for fam in vendor.families:
            tags = rng.sample(SIZE_TAGS, 5)
            for i in range(5):
                no = fam.first_no + i * fam.step
                pn = f"{fam.prefix}{no}"
                parts.append(
                    PartPlan(
                        vendor,
                        fam,
                        i,
                        pn,
                        f"{vendor.series} {fam.title} {tags[i]}",
                        sample_spec(fam, rng),
                    )
                )
    return parts


def candidates_for(orig: PartPlan, parts: list[PartPlan]) -> list[PartPlan]:
    o = orig.full_spec()
    return [
        p
        for p in parts
        if p.lifecycle != "discontinued"
        and p.revision == "1.0"
        and is_candidate_for(o, p.full_spec())
    ]
