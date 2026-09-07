"""Typed property-preset contract used by extraction workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any
from ._shared import (
    AgentPrompts,
    default_models,
    default_fact_fields,
    default_rag_settings,
)


@dataclass(frozen=True)
class PropertyExtractionPreset:
    """Domain configuration shared by every stage of property extraction.

    Presets contain domain policy only. File locations, provider credentials,
    paper selection, retry policy, and runtime output paths belong to runners.
    """

    name: str
    main_property_keyword: str
    main_extraction_keyword: str
    property_keywords: dict[str, Any]
    identifier_query: str = ""
    extraction_instructions: str = ""
    retrieval_queries: tuple[str, ...] = ()
    examples: tuple[dict, ...] = ()
    allowed_units: tuple[str, ...] = ()
    required_conditions: tuple[str, ...] = ()
    text_candidate_patterns: tuple[str, ...] = ()
    evidence_providers: tuple[str, ...] = (
        "rule_text",
        "table",
        "figure",
        "equation",
    )
    processing_kwargs: dict[str, Any] = field(default_factory=dict)
    models: dict[str, dict[str, Any]] = field(default_factory=default_models)
    agent_prompts: AgentPrompts = field(default_factory=AgentPrompts)
    fact_fields: dict[str, Any] = field(default_factory=default_fact_fields)
    # Omitted modalities inherit the property keyword policy; empty tuples select none.
    modality_patterns: dict[str, tuple[str, ...]] = field(default_factory=dict)
    rag_settings: dict[str, Any] = field(default_factory=default_rag_settings)
    property_aliases: tuple[str, ...] = ()
    legacy_fields: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        """Reject incomplete configuration before parsing or model calls.

        Unit and condition policies are advisory: downstream processing can
        flag unexpected values for review, but must preserve the extracted fact.
        """
        if not isinstance(self.agent_prompts, AgentPrompts):
            raise ValueError("agent_prompts must be AgentPrompts")
        if (
            not {"material_reported", "property", "value", "unit"}
            <= self.fact_fields.keys()
        ):
            raise ValueError(
                "fact_fields must include material_reported, property, value and unit"
            )
        import json

        json.dumps(self.fact_fields, allow_nan=False)
        for role in ("identifier", "extractor", "vision"):
            settings = self.models.get(role)
            if not isinstance(settings, dict) or (
                role != "vision" and not settings.get("model")
            ):
                raise ValueError(f"Missing model settings for {role}")
            if set(settings) - {"model", "base_url", "api_key_env", "parameters"}:
                raise ValueError(
                    f"Unknown model setting for {role}; secrets belong in environment variables"
                )
            params = settings.get("parameters", {})
            if not isinstance(params, dict) or set(params) & {
                "model",
                "messages",
                "api_key",
                "api_base",
                "timeout",
            }:
                raise ValueError(f"Invalid model parameters for {role}")
        for modality, patterns in self.modality_patterns.items():
            if modality not in {"table", "figure", "equation"} or not isinstance(
                patterns, tuple
            ):
                raise ValueError(
                    "modality_patterns supports table, figure and equation tuples"
                )
            for pattern in patterns:
                re.compile(pattern)
        for name in (
            "name",
            "main_property_keyword",
            "main_extraction_keyword",
            "identifier_query",
            "extraction_instructions",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.name):
            raise ValueError("name must be a lowercase Python module name")
        for name in (
            "text_candidate_patterns",
            "evidence_providers",
            "retrieval_queries",
            "allowed_units",
            "required_conditions",
        ):
            value = getattr(self, name)
            if not isinstance(value, tuple) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise ValueError(f"{name} must be a tuple of non-empty strings")
            if len(value) != len(set(value)):
                raise ValueError(f"{name} must not contain duplicates")
        if not self.evidence_providers:
            raise ValueError("evidence_providers cannot be empty")
        supported = {"rule_text", "physbert", "table", "equation", "figure"}
        unknown = set(self.evidence_providers) - supported
        if unknown:
            raise ValueError(
                "Unknown evidence provider(s): " + ", ".join(sorted(unknown))
            )
        if not self.retrieval_queries:
            raise ValueError(
                "retrieval_queries cannot be empty; RAG must be selectable"
            )
        if not self.allowed_units:
            raise ValueError(
                "allowed_units cannot be empty (use '1' for dimensionless values)"
            )
        if not isinstance(self.examples, tuple) or any(
            not isinstance(example, dict) or not example for example in self.examples
        ):
            raise ValueError("examples must be a tuple of non-empty dictionaries")
        if not isinstance(self.processing_kwargs, dict):
            raise ValueError("processing_kwargs must be a dictionary")

        patterns = list(self.text_candidate_patterns)
        if not isinstance(self.property_keywords, dict) or not self.property_keywords:
            raise ValueError("property_keywords must be a non-empty dictionary")
        has_signal = False
        for name in ("exact_keywords", "substring_keywords", "regex_keywords"):
            values = self.property_keywords.get(name, [])
            if not isinstance(values, (list, tuple)) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(
                    f"property_keywords.{name} must contain non-empty strings"
                )
            has_signal = has_signal or bool(values)
            if name == "regex_keywords":
                patterns.extend(values)
        candidates = self.property_keywords.get("candidate_patterns", [])
        if not isinstance(candidates, (list, tuple)):
            raise ValueError("property_keywords.candidate_patterns must be a sequence")
        for candidate in candidates:
            if (
                not isinstance(candidate, dict)
                or not isinstance(candidate.get("pattern"), str)
                or not candidate["pattern"].strip()
            ):
                raise ValueError(
                    "Each candidate pattern needs a non-empty 'pattern' string"
                )
            patterns.append(candidate["pattern"])
        if not (has_signal or candidates):
            raise ValueError(
                "property_keywords needs at least one supported keyword or pattern"
            )
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"Invalid preset regex {pattern!r}: {exc}") from exc
