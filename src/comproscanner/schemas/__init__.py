"""Stable data contracts shared by processors and extraction pipelines."""

from .article_csv import (
    ARTICLE_CSV_COLUMNS,
    ArticleCSVSchemaError,
    normalize_legacy_article_frame,
    validate_article_frame,
)

__all__ = [
    "ARTICLE_CSV_COLUMNS",
    "ArticleCSVSchemaError",
    "normalize_legacy_article_frame",
    "validate_article_frame",
]
