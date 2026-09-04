"""Pluggable fact processing kept separate from evidence discovery."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .models import Fact


class MaterialNormalizer(Protocol):
    def normalize(self, material: str) -> tuple[str, str]: ...


class IdentityMaterialNormalizer:
    """Safe default: preserve the reported material until a parser is enabled."""

    def normalize(self, material: str) -> tuple[str, str]:
        value = material.strip()
        return value, value


class MaterialParserAPINormalizer:
    """Resolve formulas through the legacy Material Parsers HTTP service.

    The adapter is independent from CrewAI and is only constructed when a run
    explicitly enables network-backed material normalization.
    """

    endpoint = "https://lfoppiano-material-parsers.hf.space/process/material"

    def __init__(self, resolver: Callable[[str], str | None] | None = None):
        self._resolver = resolver or self._resolve_http
        self._cache: dict[str, str] = {}

    def _resolve_http(self, material: str) -> str | None:
        import requests

        response = requests.post(
            self.endpoint, files={"text": (None, material)}, timeout=30
        )
        response.raise_for_status()
        payload = response.json()
        try:
            values = payload[0][0].get("resolvedFormulas", [])
            return str(values[0].get("rawValue", "")).strip() or None
        except (IndexError, KeyError, TypeError, AttributeError):
            return None

    def normalize(self, material: str) -> tuple[str, str]:
        reported = material.strip()
        if reported in self._cache:
            normalized = self._cache[reported]
            return normalized, normalized
        try:
            normalized = self._resolver(reported) or reported
        except Exception:
            normalized = reported
        normalized = normalized.strip()
        self._cache[reported] = normalized
        return normalized, normalized


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
            material_reported_variants=fact.material_reported_variants,
        )
