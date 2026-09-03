"""Traceable source evidence for extracted material-property facts."""

from .models import Evidence, EvidenceType, RetrievalMethod
from .registry import EvidenceProviderRegistry
from .text import TextEvidenceBuilder

__all__ = [
    "Evidence",
    "EvidenceProviderRegistry",
    "EvidenceType",
    "RetrievalMethod",
    "TextEvidenceBuilder",
]
