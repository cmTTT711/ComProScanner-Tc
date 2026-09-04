"""Conservative fact merging without hidden value or unit conversions."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
import re
import unicodedata

from .models import Fact


_DASHES = str.maketrans(
    {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-"}
)
_EXPLICIT_ACRONYM = re.compile(
    r"^(?P<name>.+?)\s*\((?P<alias>[A-Z][A-Z0-9-]{1,9})\)$"
)


def _conservative_material_key(value: str) -> str:
    """Normalize typography only; retain composition and sample-state words."""

    text = unicodedata.normalize("NFKC", value).translate(_DASHES).strip()
    match = _EXPLICIT_ACRONYM.fullmatch(text)
    if match:
        text = match.group("name").strip()
    # A frequent PDF extraction error renders decimal points as colons.
    text = re.sub(r"(?<=\d):(?=\d)", ".", text)
    text = re.sub(r"\s+", "", text)
    return text.casefold()


def _merge_key(fact: Fact) -> tuple:
    original = fact.merge_key()
    return (
        *original[:2],
        _conservative_material_key(fact.material_identity_key),
        *original[3:],
    )


def merge_facts(facts: Iterable[Fact]) -> list[Fact]:
    """Merge typography-equivalent facts and retain evidence and reported names."""

    merged: OrderedDict[tuple, Fact] = OrderedDict()
    for fact in facts:
        key = _merge_key(fact)
        existing = merged.get(key)
        if existing is None:
            merged[key] = fact
            continue
        evidence_ids = tuple(dict.fromkeys([*existing.evidence_ids, *fact.evidence_ids]))
        reported_variants = tuple(
            dict.fromkeys(
                [
                    *(existing.material_reported_variants or (existing.material_reported,)),
                    *(fact.material_reported_variants or (fact.material_reported,)),
                ]
            )
        )
        merged[key] = Fact(
            document_id=existing.document_id,
            property_name=existing.property_name,
            material_reported=existing.material_reported,
            material_normalized=existing.material_normalized,
            material_identity_key=existing.material_identity_key,
            fact_value=existing.fact_value,
            evidence_ids=evidence_ids,
            conditions=existing.conditions,
            material_reported_variants=reported_variants,
        )
    return list(merged.values())
