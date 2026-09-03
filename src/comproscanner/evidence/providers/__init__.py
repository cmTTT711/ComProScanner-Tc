"""Built-in evidence providers."""

from .equation import EquationEvidenceProvider
from .figure import FigureEvidenceProvider
from .rule_text import RuleTextEvidenceProvider
from .table import TableEvidenceProvider
from .vector_text import VectorTextEvidenceProvider

__all__ = [
    "EquationEvidenceProvider",
    "FigureEvidenceProvider",
    "RuleTextEvidenceProvider",
    "TableEvidenceProvider",
    "VectorTextEvidenceProvider",
]
