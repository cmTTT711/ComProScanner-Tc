from .base_urls import BaseUrls
from .paths_config import DefaultPaths
from .rag_config import RAGConfig
from .database_config import DatabaseConfig
from .article_keywords import ArticleRelatedKeywords
from .custom_dictionary import CustomDictionary


def __getattr__(name):
    """Keep CrewAI/LiteLLM optional until LLMConfig is actually requested."""
    if name == "LLMConfig":
        from .llm_config import LLMConfig

        return LLMConfig
    raise AttributeError(name)

__all__ = [
    "BaseUrls",
    "DefaultPaths",
    "RAGConfig",
    "DatabaseConfig",
    "ArticleRelatedKeywords",
    "LLMConfig",
    "CustomDictionary",
]
