"""Rule selection over canonical text chunks."""

from __future__ import annotations

from collections.abc import Iterable

from comproscanner.evidence.chunking import TextChunk
from comproscanner.evidence.text import TextChunkMatch
from comproscanner.evidence.providers.base import find_patterns


class RuleTextEvidenceProvider:
    name = "rule"

    def __init__(self, patterns: Iterable[str]):
        self.patterns = tuple(patterns)

    def select(self, units: Iterable[TextChunk]) -> list[TextChunkMatch]:
        matches: list[TextChunkMatch] = []
        for chunk in units:
            matched = find_patterns(chunk.content, self.patterns)
            if matched:
                matches.append(
                    TextChunkMatch(
                        chunk_id=chunk.chunk_id,
                        provider=self.name,
                        details={"matched_patterns": matched},
                    )
                )
        return matches
