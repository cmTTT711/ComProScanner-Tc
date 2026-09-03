"""Normalized, evidence-backed material-property facts."""

from .models import Fact, FactValue
from .merger import merge_facts
from .processors import (
    FactProcessor,
    IdentityMaterialNormalizer,
    MaterialNormalizer,
    MaterialParserAPINormalizer,
)

__all__ = [
    "Fact",
    "FactProcessor",
    "FactValue",
    "IdentityMaterialNormalizer",
    "MaterialParserAPINormalizer",
    "MaterialNormalizer",
    "merge_facts",
]
