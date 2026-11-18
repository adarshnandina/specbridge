"""ComponentSpec (schema_version 1): every field is a FieldValue{value, unit, page, quote} or null."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1"


class FieldValue(BaseModel):
    """A value exactly as printed (un-normalised), with its evidence."""

    value: str | float | int | list[str] | list[float] | None = Field(
        description="Value as printed in the datasheet; lists for certifications, interfaces "
        "and dimensions [w, h, d]"
    )
    unit: str | None = Field(default=None, description="Unit as printed, e.g. 'V', 'mA', '°C'")
    page: int | None = Field(default=None, description="1-based page number where it appears")
    quote: str | None = Field(default=None, description="Short verbatim quote from that page")


class ComponentSpec(BaseModel):
    part_number: FieldValue | None = None
    manufacturer: FieldValue | None = None
    product_name: FieldValue | None = None
    category: FieldValue | None = Field(
        default=None, description="one of: sensor, drive, io_module, power_supply, other"
    )
    supply_voltage_min_v: FieldValue | None = None
    supply_voltage_max_v: FieldValue | None = None
    rated_current_a: FieldValue | None = None
    power_w: FieldValue | None = None
    operating_temp_min_c: FieldValue | None = None
    operating_temp_max_c: FieldValue | None = None
    ip_rating: FieldValue | None = None
    certifications: FieldValue | None = None
    interfaces: FieldValue | None = None
    dimensions_mm: FieldValue | None = Field(
        default=None, description="[width, height, depth] in the printed unit"
    )
    weight_g: FieldValue | None = None
    datasheet_revision: FieldValue | None = None


class ValidationIssue(BaseModel):
    field: str
    rule: str
    message: str
    severity: str = "error"  # error | warning


def spec_to_dict(spec: ComponentSpec) -> dict[str, Any]:
    return {k: (v.model_dump() if v is not None else None) for k, v in spec}
