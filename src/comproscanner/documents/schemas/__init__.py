"""Stable data contracts shared by processors and extraction pipelines."""

from comproscanner.documents.schemas.article_csv import ARTICLE_CSV_COLUMNS
from comproscanner.documents.schemas.article_csv import ArticleCSVSchemaError
from comproscanner.documents.schemas.article_csv import normalize_legacy_article_frame
from comproscanner.documents.schemas.article_csv import validate_article_frame

__all__ = [
    "ARTICLE_CSV_COLUMNS",
    "ArticleCSVSchemaError",
    "normalize_legacy_article_frame",
    "validate_article_frame",
]
