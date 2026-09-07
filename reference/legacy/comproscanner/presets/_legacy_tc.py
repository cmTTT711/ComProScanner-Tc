"""Explicit import compatibility for historical Tc gold and prediction files."""

from __future__ import annotations

from typing import Any


def adapt_legacy_tc_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Tc column names without guessing the property of generic records.

    Modern records pass through unchanged. Legacy records retain review metadata
    and conditions; the input records are never modified.
    """

    converted = []
    for item in records:
        record = dict(item)
        if "tc_value" in record or "tc_unit" in record:
            property_name = record.get("property", record.get("property_name"))
            if property_name is not None and str(
                property_name
            ).strip().casefold() not in {
                "tc",
                "curie_temperature",
                "curie temperature",
            }:
                raise ValueError("Legacy tc_value/tc_unit fields require a Tc property")
            if property_name is None:
                record["property"] = "Tc"
            for old_name, new_name in (("tc_value", "value"), ("tc_unit", "unit")):
                if old_name in record:
                    legacy_value = record.pop(old_name)
                    if (
                        new_name in record
                        and str(record[new_name]).strip() != str(legacy_value).strip()
                    ):
                        raise ValueError(
                            f"Conflicting {old_name} and {new_name} fields"
                        )
                    record[new_name] = legacy_value
        converted.append(record)
    return converted
