"""Exact, reproducible evaluation for normalized material-property facts."""

from comproscanner.results.evaluation.strict import StrictMetrics
from comproscanner.results.evaluation.strict import score_exact_facts

__all__ = ["StrictMetrics", "score_exact_facts"]
