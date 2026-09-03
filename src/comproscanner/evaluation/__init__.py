"""Exact, reproducible evaluation for normalized material-property facts."""

from .strict import StrictMetrics, score_exact_facts

__all__ = ["StrictMetrics", "score_exact_facts"]
