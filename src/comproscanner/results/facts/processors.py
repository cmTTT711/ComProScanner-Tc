"""Pluggable fact processing kept separate from evidence discovery."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from comproscanner.results.facts.models import Fact


class MaterialNormalizer(Protocol):
    def normalize(self, material: str) -> tuple[str, str]: ...


@dataclass(frozen=True)
class NormalizationResult:
    """A material identity plus reviewable diagnostics, without mutable error state."""

    normalized: str
    identity_key: str
    processing_issues: tuple[str, ...] = ()
    material_resolution: tuple[dict, ...] = ()


def _failure_issue(error: Exception) -> str:
    status = getattr(getattr(error, "response", None), "status_code", None)
    detail = f"HTTP {status}" if status is not None else type(error).__name__
    return f"material_normalization_failed: {detail}"


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

    def __init__(
        self,
        resolver: Callable[[str], str | Sequence[str] | None] | None = None,
    ):
        self._resolver = resolver or self._resolve_http
        self._cache: dict[str, NormalizationResult] = {}

    def _resolve_http(self, material: str) -> tuple[str, ...]:
        import requests

        response = requests.post(
            self.endpoint, files={"text": (None, material)}, timeout=30
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Material parser response must be a list")
        resolved = []
        for group in payload:
            if not isinstance(group, list):
                raise ValueError("Material parser response groups must be lists")
            for item in group:
                values = item.get("resolvedFormulas", [])
                if not isinstance(values, list):
                    raise ValueError("resolvedFormulas must be a list")
                for value in values:
                    raw_value = value.get("rawValue", "")
                    if not isinstance(raw_value, str):
                        raise ValueError("Resolved formula must be text")
                    if raw_value.strip():
                        resolved.append(raw_value.strip())
        return tuple(resolved)

    def normalize(self, material: str) -> tuple[str, str]:
        result = self.normalize_with_diagnostics(material)
        return result.normalized, result.identity_key

    def normalize_with_diagnostics(self, material: str) -> NormalizationResult:
        """Accept only one resolved identity; preserve unresolved/ambiguous inputs."""

        reported = material.strip()
        if reported in self._cache:
            return self._cache[reported]
        try:
            resolved = self._resolver(reported)
            values = (resolved,) if isinstance(resolved, str) else (resolved or ())
            if not isinstance(values, Sequence) or any(
                not isinstance(value, str) for value in values
            ):
                raise ValueError("Material resolver must return text candidates")
            candidates = tuple(
                dict.fromkeys(value.strip() for value in values if value.strip())
            )
        except Exception as error:
            return NormalizationResult(reported, reported, (_failure_issue(error),))
        if not candidates:
            return NormalizationResult(
                reported, reported, ("material_normalization_empty",)
            )
        if len(candidates) > 1:
            return NormalizationResult(
                reported,
                reported,
                (f"material_normalization_ambiguous: {' | '.join(candidates)}",),
            )
        result = NormalizationResult(candidates[0], candidates[0])
        self._cache[reported] = result
        return result


class FactProcessor:
    def __init__(
        self,
        material_normalizer: MaterialNormalizer | None = None,
        *,
        allowed_units: tuple[str, ...] = (),
        required_conditions: tuple[str, ...] = (),
    ):
        self.material_normalizer = material_normalizer or IdentityMaterialNormalizer()
        self.allowed_units = allowed_units
        self.required_conditions = required_conditions

    def process(self, fact: Fact) -> Fact:
        reported = fact.material_reported.strip()
        try:
            resolve_fact = getattr(self.material_normalizer, "normalize_fact", None)
            diagnose = getattr(
                self.material_normalizer, "normalize_with_diagnostics", None
            )
            if callable(resolve_fact):
                result = resolve_fact(fact)
            elif callable(diagnose):
                result = diagnose(fact.material_reported)
            else:
                normalized, identity_key = self.material_normalizer.normalize(
                    fact.material_reported
                )
                result = NormalizationResult(normalized, identity_key)
            if not result.normalized.strip() or not result.identity_key.strip():
                result = NormalizationResult(
                    reported,
                    reported,
                    (*result.processing_issues, "material_normalization_empty"),
                )
        except Exception as error:
            result = NormalizationResult(reported, reported, (_failure_issue(error),))

        issues = [*fact.processing_issues, *result.processing_issues]
        if (
            self.allowed_units
            and fact.fact_value.unit.strip() not in self.allowed_units
        ):
            issues.append(f"unsupported_unit: {fact.fact_value.unit}")
        for name in self.required_conditions:
            value = fact.conditions.get(name)
            if (
                value is None
                or (isinstance(value, str) and not value.strip())
                or (isinstance(value, (list, tuple, dict)) and not value)
            ):
                issues.append(f"missing_condition: {name}")
        return replace(
            fact,
            material_normalized=result.normalized,
            material_identity_key=result.identity_key,
            processing_issues=tuple(dict.fromkeys(issues)),
            material_resolution=(
                *fact.material_resolution,
                *result.material_resolution,
            ),
        )
