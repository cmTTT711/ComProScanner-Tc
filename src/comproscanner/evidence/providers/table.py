"""Create table evidence while retaining headers, units, rows, and footnotes."""

from __future__ import annotations

from dataclasses import dataclass

from comproscanner.evidence.models import Evidence
from comproscanner.evidence.models import EvidenceType
from comproscanner.evidence.models import RetrievalMethod
from comproscanner.evidence.providers.base import find_patterns


@dataclass(frozen=True)
class TableUnit:
    table_id: str
    document_id: str
    caption: str
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    footnotes: tuple[str, ...] = ()
    page: int | None = None
    raw_content: str = ""

    def render(self) -> str:
        if self.raw_content.strip():
            return self.raw_content.strip()
        lines = [self.caption.strip(), " | ".join(self.headers)]
        lines.extend(" | ".join(row) for row in self.rows)
        lines.extend(self.footnotes)
        return "\n".join(line for line in lines if line.strip())


class TableEvidenceProvider:
    name = "table_rule"

    def __init__(self, patterns: tuple[str, ...]):
        self.patterns = patterns

    def select(self, units: list[TableUnit], target_property: str) -> list[Evidence]:
        evidence: list[Evidence] = []
        for unit in units:
            content = unit.render()
            matched = find_patterns(content, self.patterns)
            if not matched:
                continue
            evidence.append(
                Evidence(
                    evidence_id=unit.table_id,
                    document_id=unit.document_id,
                    target_property=target_property,
                    source_type=EvidenceType.TABLE,
                    source_id=unit.table_id,
                    content=content,
                    retrieval_methods=(
                        RetrievalMethod(self.name, {"matched_patterns": matched}),
                    ),
                    page_start=unit.page,
                    page_end=unit.page,
                )
            )
        return evidence
