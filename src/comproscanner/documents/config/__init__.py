"""Source-format settings and intermediate Article locations."""

from .article_keywords import ArticleRelatedKeywords
from .base_urls import BaseUrls
from .paths import DefaultPaths


class ArticlePaths:
    """Intermediate CSV naming retained for source processor interoperability."""

    def __init__(self, main_property_keyword):
        self.EXTRACTED_CSV_FOLDERPATH = (
            f"results/extracted_data/{main_property_keyword}"
        )
