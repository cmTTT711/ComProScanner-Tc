"""Pluggable article-source descriptions and canonical CSV normalization."""

from .registry import ArticleSource, ArticleSourceRegistry, default_source_registry
from .normalize import normalize_article_csvs
from .process import (
    ArticleProcessingPlan,
    build_processing_plan,
    execute_processing_plan,
    format_processing_plan,
    read_doi_file,
)

__all__ = [
    "ArticleSource",
    "ArticleSourceRegistry",
    "default_source_registry",
    "normalize_article_csvs",
    "ArticleProcessingPlan",
    "build_processing_plan",
    "execute_processing_plan",
    "format_processing_plan",
    "read_doi_file",
]
