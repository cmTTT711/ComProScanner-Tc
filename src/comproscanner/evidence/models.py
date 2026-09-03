"""Small, serializable evidence data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class EvidenceType(StrEnum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    EQUATION = "equation"


@dataclass(frozen=True)
class RetrievalMethod:
    """How a source unit was selected; not a separate evidence type."""

    provider: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    """Original source evidence passed to an identifier or extractor."""

    evidence_id: str
    document_id: str
    target_property: str
    source_type: EvidenceType
    source_id: str
    content: str
    retrieval_methods: tuple[RetrievalMethod, ...]
    section: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id cannot be empty")
        if not self.document_id.strip():
            raise ValueError("document_id cannot be empty")
        if not self.content.strip():
            raise ValueError("Evidence must preserve non-empty source content")
        if not self.retrieval_methods:
            raise ValueError("Evidence must record at least one retrieval method")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_type"] = self.source_type.value
        return data
