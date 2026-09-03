"""Pluggable fact processing kept separate from evidence discovery."""

from __future__ import annotations

from typing import Protocol

from .models import Fact


class MaterialNormalizer(Protocol):
    def normalize(self, material: str) -> tuple[str, str]: ...


class IdentityMaterialNormalizer:
    """Safe default: preserve the reported material until a parser is enabled."""

    def normalize(self, material: str) -> tuple[str, str]:
        value = material.strip()
        return value, value


class FactProcessor:
    def __init__(self, material_normalizer: MaterialNormalizer | None = None):
        self.material_normalizer = material_normalizer or IdentityMaterialNormalizer()

    def process(self, fact: Fact) -> Fact:
        normalized, identity_key = self.material_normalizer.normalize(
            fact.material_reported
        )
        return Fact(
            document_id=fact.document_id,
            property_name=fact.property_name,
            material_reported=fact.material_reported,
            material_normalized=normalized,
            material_identity_key=identity_key,
            fact_value=fact.fact_value,
            evidence_ids=fact.evidence_ids,
            conditions=fact.conditions,
        )
