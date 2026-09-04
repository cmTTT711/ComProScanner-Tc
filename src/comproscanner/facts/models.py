"""Fact contracts kept independent from CrewAI and model providers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class FactValue:
    """A reported value without implicit unit conversion or approximation loss."""

    value: Decimal | str
    unit: str
    qualifier: str | None = None

    @classmethod
    def from_raw(
        cls, value: int | float | Decimal | str, unit: str, qualifier: str | None = None
    ) -> "FactValue":
        if isinstance(value, float):
            value = Decimal(str(value))
        elif isinstance(value, int):
            value = Decimal(value)
        return cls(value=value, unit=unit.strip(), qualifier=qualifier)

    def stable_value(self) -> str:
        if isinstance(self.value, Decimal):
            return format(self.value.normalize(), "f")
        return str(self.value).strip()


@dataclass(frozen=True)
class Fact:
    """One material-property assertion with one or more original evidences."""

    document_id: str
    property_name: str
    material_reported: str
    material_normalized: str
    material_identity_key: str
    fact_value: FactValue
    evidence_ids: tuple[str, ...]
    conditions: dict[str, Any] = field(default_factory=dict)
    material_reported_variants: tuple[str, ...] = field(default_factory=tuple)

    def merge_key(self) -> tuple[str, str, str, str, str, str | None]:
        return (
            self.document_id.strip(),
            self.property_name.strip().casefold(),
            self.material_identity_key.strip().casefold(),
            self.fact_value.stable_value(),
            self.fact_value.unit.strip(),
            self.fact_value.qualifier,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data["material_reported_variants"]:
            data["material_reported_variants"] = [self.material_reported]
        data["fact_value"]["value"] = self.fact_value.stable_value()
        return data
