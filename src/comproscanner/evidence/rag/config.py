"""Resolved embedding settings supplied by the selected property preset."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RAGConfig:
    rag_db_path: str
    embedding_model: str
    rag_max_tokens: int = 512
    rag_top_k: int = 3
    enabled: bool = True
