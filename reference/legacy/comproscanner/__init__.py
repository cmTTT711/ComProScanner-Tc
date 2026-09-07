"""Public ComProScanner API with lightweight, lazy imports.

Importing this package or its CLI must not initialize CrewAI, LiteLLM,
embedding models, databases, or telemetry. The historical public API remains
available and loads its heavy implementation only when called.
"""

from __future__ import annotations

from typing import Any

__version__ = "0.1.4"

__all__ = [
    "ComProScanner",
    "RAGConfig",
    "LLMConfig",
    "collect_metadata",
    "process_articles",
    "extract_composition_property_data",
    "clean_data",
    "evaluate_semantic",
    "evaluate_agentic",
]


def __getattr__(name: str):
    if name == "ComProScanner":
        from .comproscanner import ComProScanner

        return ComProScanner
    if name == "RAGConfig":
        from .utils.configs.rag_config import RAGConfig

        return RAGConfig
    if name == "LLMConfig":
        from .utils.configs.llm_config import LLMConfig

        return LLMConfig
    raise AttributeError(name)


def _scanner(main_property_keyword: str):
    from .comproscanner import ComProScanner

    return ComProScanner(main_property_keyword=main_property_keyword)


def collect_metadata(main_property_keyword: str, **kwargs: Any):
    return _scanner(main_property_keyword).collect_metadata(**kwargs)


def process_articles(
    main_property_keyword: str,
    property_keywords: dict | None = None,
    source_list: list | None = None,
    **kwargs: Any,
):
    if source_list is None:
        source_list = ["elsevier", "wiley", "iop", "springer", "pdfs"]
    return _scanner(main_property_keyword).process_articles(
        property_keywords=property_keywords, source_list=source_list, **kwargs
    )


def extract_composition_property_data(
    main_property_keyword: str,
    main_extraction_keyword: str | None = None,
    **kwargs: Any,
):
    return _scanner(main_property_keyword).extract_composition_property_data(
        main_extraction_keyword=main_extraction_keyword, **kwargs
    )


def clean_data(main_property_keyword: str, **kwargs: Any):
    return _scanner(main_property_keyword).clean_data(**kwargs)


def evaluate_semantic(**kwargs: Any):
    return _scanner("placeholder").evaluate_semantic(**kwargs)


def evaluate_agentic(**kwargs: Any):
    return _scanner("placeholder").evaluate_agentic(**kwargs)
