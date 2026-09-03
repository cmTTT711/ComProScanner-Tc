"""Conservative fact merging: identical values only, no hidden conversions."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable

from .models import Fact


def merge_facts(facts: Iterable[Fact]) -> list[Fact]:
    """Merge exact facts and retain every distinct supporting evidence ID."""

    merged: OrderedDict[tuple, Fact] = OrderedDict()
    for fact in facts:
        key = fact.merge_key()
        existing = merged.get(key)
        if existing is None:
            merged[key] = fact
            continue
        evidence_ids = tuple(dict.fromkeys([*existing.evidence_ids, *fact.evidence_ids]))
        merged[key] = Fact(
            document_id=existing.document_id,
            property_name=existing.property_name,
            material_reported=existing.material_reported,
            material_normalized=existing.material_normalized,
            material_identity_key=existing.material_identity_key,
            fact_value=existing.fact_value,
            evidence_ids=evidence_ids,
            conditions=existing.conditions,
        )
    return list(merged.values())
