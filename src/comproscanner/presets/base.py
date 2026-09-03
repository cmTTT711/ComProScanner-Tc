"""Typed property-preset contract used by extraction workflows."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PropertyExtractionPreset:
    """Complete, immutable configuration for one extracted property.

    Presets contain domain policy only. File locations, provider credentials,
    paper selection, retry policy, and runtime output paths belong to runners.
    """

    name: str
    main_property_keyword: str
    main_extraction_keyword: str
    property_keywords: dict[str, Any]
    text_candidate_patterns: tuple[str, ...] = ()
    evidence_providers: tuple[str, ...] = (
        "rule_text",
        "table",
        "figure",
        "equation",
    )
    processing_kwargs: dict[str, Any] = field(default_factory=dict)
    extraction_kwargs: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Raise ``ValueError`` when required preset fields are incomplete."""
        if not self.name.strip():
            raise ValueError("Preset name cannot be empty")
        if not self.main_property_keyword.strip():
            raise ValueError("main_property_keyword cannot be empty")
        if not self.main_extraction_keyword.strip():
            raise ValueError("main_extraction_keyword cannot be empty")
        if not self.property_keywords:
            raise ValueError("property_keywords cannot be empty")
        if not self.evidence_providers:
            raise ValueError("evidence_providers cannot be empty")

    def to_runtime_dict(self) -> dict[str, Any]:
        """Return the historical dictionary shape expected by ComProScanner."""
        self.validate()
        extraction_kwargs = deepcopy(self.extraction_kwargs)
        extraction_kwargs.setdefault(
            "main_extraction_keyword", self.main_extraction_keyword
        )
        return {
            "main_property_keyword": self.main_property_keyword,
            "property_keywords": deepcopy(self.property_keywords),
            "processing_kwargs": deepcopy(self.processing_kwargs),
            "extraction_kwargs": extraction_kwargs,
        }
