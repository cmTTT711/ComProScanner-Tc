"""Unify rule and PhysBERT selections over canonical text chunks."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from comproscanner.evidence.chunking import TextChunk
from comproscanner.evidence.models import Evidence
from comproscanner.evidence.models import EvidenceType
from comproscanner.evidence.models import RetrievalMethod


@dataclass(frozen=True)
class TextChunkMatch:
    chunk_id: str
    provider: str
    details: dict[str, Any] = field(default_factory=dict)


class TextEvidenceBuilder:
    """Create one TextEvidence per selected chunk, preserving all selectors."""

    def build(
        self,
        *,
        chunks: Iterable[TextChunk],
        matches: Iterable[TextChunkMatch],
        target_property: str,
    ) -> list[Evidence]:
        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        methods_by_id: dict[str, list[RetrievalMethod]] = defaultdict(list)
        seen_methods: set[tuple[str, str, str]] = set()
        for match in matches:
            if match.chunk_id not in chunks_by_id:
                raise KeyError(f"Unknown canonical chunk: {match.chunk_id}")
            key = (match.chunk_id, match.provider, repr(sorted(match.details.items())))
            if key in seen_methods:
                continue
            seen_methods.add(key)
            methods_by_id[match.chunk_id].append(
                RetrievalMethod(provider=match.provider, details=match.details)
            )

        evidence: list[Evidence] = []
        for chunk in chunks_by_id.values():
            methods = methods_by_id.get(chunk.chunk_id)
            if not methods:
                continue
            evidence.append(
                Evidence(
                    evidence_id=f"{chunk.chunk_id}_TEXT",
                    document_id=chunk.document_id,
                    target_property=target_property,
                    source_type=EvidenceType.TEXT,
                    source_id=chunk.chunk_id,
                    content=chunk.content,
                    retrieval_methods=tuple(methods),
                    section=chunk.section,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    metadata={"word_count": chunk.word_count},
                )
            )
        return evidence
