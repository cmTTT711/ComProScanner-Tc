"""Pluggable article-source descriptions and canonical CSV normalization."""

from comproscanner.documents.ingestion.registry import ArticleSource
from comproscanner.documents.ingestion.registry import ArticleSourceRegistry
from comproscanner.documents.ingestion.registry import default_source_registry
from comproscanner.documents.ingestion.normalize import normalize_article_csvs
from comproscanner.documents.ingestion.process import ArticleProcessingPlan
from comproscanner.documents.ingestion.process import build_processing_plan
from comproscanner.documents.ingestion.process import execute_processing_plan
from comproscanner.documents.ingestion.process import format_processing_plan
from comproscanner.documents.ingestion.process import read_doi_file

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
