"""Adapter between canonical TextChunks and the existing Chroma manager."""

from __future__ import annotations

import re


class CanonicalChunkVectorStore:
    def __init__(self, manager):
        self.manager = manager

    @staticmethod
    def database_name(document_id: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", document_id).strip("_")

    def index_chunks(self, document_id: str, chunks: list) -> None:
        self.manager.create_chunk_database(self.database_name(document_id), chunks)

    def search_chunks(self, document_id: str, query: str, top_k: int) -> list[dict]:
        return self.manager.query_chunks(
            self.database_name(document_id), query=query, top_k=top_k
        )
