"""Built-in evidence providers."""

from comproscanner.evidence.providers.equation import EquationEvidenceProvider
from comproscanner.evidence.providers.figure import FigureEvidenceProvider
from comproscanner.evidence.providers.rule_text import RuleTextEvidenceProvider
from comproscanner.evidence.providers.table import TableEvidenceProvider
from comproscanner.evidence.providers.vector_text import VectorTextEvidenceProvider

__all__ = [
    "EquationEvidenceProvider",
    "FigureEvidenceProvider",
    "RuleTextEvidenceProvider",
    "TableEvidenceProvider",
    "VectorTextEvidenceProvider",
]
