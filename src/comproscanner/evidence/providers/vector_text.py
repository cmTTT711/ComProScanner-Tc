"""Map PhysBERT/vector results back to canonical text chunks."""

from __future__ import annotations

from collections.abc import Iterable

from comproscanner.evidence.chunking import TextChunk
from comproscanner.evidence.text import TextChunkMatch


class VectorTextEvidenceProvider:
    name = "physbert"

    def __init__(self, vector_store):
        """Accept a store exposing ``index_chunks`` and ``search_chunks``."""

        self.vector_store = vector_store

    def index(self, document_id: str, chunks: Iterable[TextChunk]) -> None:
        self.vector_store.index_chunks(document_id, list(chunks))

    def select(
        self, document_id: str, queries: Iterable[str], *, top_k: int
    ) -> list[TextChunkMatch]:
        matches: list[TextChunkMatch] = []
        for query in queries:
            if not query.strip():
                continue
            for result in self.vector_store.search_chunks(document_id, query, top_k):
                matches.append(
                    TextChunkMatch(
                        chunk_id=result["chunk_id"],
                        provider=self.name,
                        details={"query": query, "score": result.get("score")},
                    )
                )
        return matches
