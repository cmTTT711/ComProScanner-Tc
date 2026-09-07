"""Traceable source evidence for extracted material-property facts."""

from comproscanner.evidence.models import Evidence
from comproscanner.evidence.models import EvidenceType
from comproscanner.evidence.models import RetrievalMethod
from comproscanner.evidence.registry import EvidenceProviderRegistry
from comproscanner.evidence.text import TextEvidenceBuilder

__all__ = [
    "Evidence",
    "EvidenceProviderRegistry",
    "EvidenceType",
    "RetrievalMethod",
    "TextEvidenceBuilder",
]
