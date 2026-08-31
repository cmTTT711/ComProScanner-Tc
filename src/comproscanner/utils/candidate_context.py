"""Candidate-context assembly for rule, vector, and hybrid extraction modes."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Optional

from .configs.rag_config import RAGConfig
from .logger import setup_logger

logger = setup_logger("comproscanner.log", module_name="candidate_context")


def _normalized_text(text: str) -> str:
    """Normalize whitespace and case for deterministic duplicate detection."""
    return re.sub(r"\s+", " ", text).strip().casefold()


def merge_candidate_context(
    rule_candidate: str, retrieved_chunks: Iterable[str]
) -> str:
    """Append unique vector chunks without removing any rule-derived context.

    The rule candidate is authoritative and always remains first. A retrieved
    chunk is omitted when its normalized text is empty, duplicates an earlier
    vector chunk, or is already wholly contained in the rule candidate.
    """
    rule_candidate = (rule_candidate or "").strip()
    normalized_rule = _normalized_text(rule_candidate)
    unique_chunks: list[str] = []
    seen: set[str] = set()

    for chunk in retrieved_chunks:
        chunk = (chunk or "").strip()
        normalized = _normalized_text(chunk)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if normalized_rule and normalized in normalized_rule:
            continue
        unique_chunks.append(chunk)

    if not unique_chunks:
        return rule_candidate

    vector_context = "\n\n".join(
        f"## RETRIEVED CHUNK {index}\n{chunk}"
        for index, chunk in enumerate(unique_chunks, start=1)
    )
    if not rule_candidate:
        return f"# PHYSBERT RETRIEVED CONTEXT\n{vector_context}"
    return (
        f"{rule_candidate}\n\n"
        f"# PHYSBERT RETRIEVED CONTEXT\n{vector_context}"
    )


def build_hybrid_candidate_context(
    doi: str,
    rule_candidate: str,
    queries: Iterable[str],
    rag_config: Optional[RAGConfig] = None,
    vector_db_manager=None,
) -> str:
    """Return rule context plus PhysBERT-retrieved chunks for one paper.

    Retrieval is additive and fail-open: a missing or unavailable vector index
    returns the complete rule candidate unchanged.
    """
    rag_config = rag_config or RAGConfig()
    db_name = doi.replace("/", "_").replace(":", "_")

    try:
        if vector_db_manager is None:
            # Lazy import keeps non-RAG runs free from vector-runtime imports.
            from .database_manager import VectorDatabaseManager

            vector_db_manager = VectorDatabaseManager(rag_config)

        if not vector_db_manager.database_exists(db_name):
            logger.warning(
                "Hybrid context requested but vector database is missing for %s; "
                "using the rule candidate only.",
                doi,
            )
            return rule_candidate

        chunks: list[str] = []
        for query in queries:
            if not query or not query.strip():
                continue
            results = vector_db_manager.query_database(
                db_name=db_name,
                query=query,
                top_k=rag_config.rag_top_k,
            )
            chunks.extend(
                document.page_content
                for document, _score in (results or [])
                if getattr(document, "page_content", "").strip()
            )
        return merge_candidate_context(rule_candidate, chunks)
    except Exception as exc:
        logger.warning(
            "PhysBERT retrieval failed for %s; using the rule candidate only: %s",
            doi,
            exc,
        )
        return rule_candidate
