"""Normalized, evidence-backed material-property facts."""

from comproscanner.results.facts.models import Fact
from comproscanner.results.facts.models import FactValue
from comproscanner.results.facts.merger import merge_facts
from comproscanner.results.facts.materials import ArticleMaterialNormalizer
from comproscanner.results.facts.materials import LocalMaterialNormalizer
from comproscanner.results.facts.materials import VariableCompositionNormalizer
from comproscanner.results.facts.processors import FactProcessor
from comproscanner.results.facts.processors import IdentityMaterialNormalizer
from comproscanner.results.facts.processors import MaterialNormalizer
from comproscanner.results.facts.processors import MaterialParserAPINormalizer
from comproscanner.results.facts.processors import NormalizationResult

__all__ = [
    "Fact",
    "ArticleMaterialNormalizer",
    "LocalMaterialNormalizer",
    "VariableCompositionNormalizer",
    "FactProcessor",
    "FactValue",
    "IdentityMaterialNormalizer",
    "MaterialParserAPINormalizer",
    "MaterialNormalizer",
    "NormalizationResult",
    "merge_facts",
]
