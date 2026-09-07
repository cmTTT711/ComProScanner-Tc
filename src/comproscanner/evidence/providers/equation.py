"""Select property-related equations together with their original context."""

from __future__ import annotations

from dataclasses import dataclass

from comproscanner.evidence.models import Evidence
from comproscanner.evidence.models import EvidenceType
from comproscanner.evidence.models import RetrievalMethod
from comproscanner.evidence.providers.base import find_patterns


@dataclass(frozen=True)
class EquationUnit:
    equation_id: str
    document_id: str
    equation: str
    nearby_text: str
    section: str | None = None
    page: int | None = None

    def render(self) -> str:
        if self.equation in self.nearby_text:
            return self.nearby_text.strip()
        return f"{self.equation}\n{self.nearby_text}".strip()


class EquationEvidenceProvider:
    name = "equation_rule"

    def __init__(self, patterns: tuple[str, ...]):
        self.patterns = patterns

    def select(self, units: list[EquationUnit], target_property: str) -> list[Evidence]:
        evidence: list[Evidence] = []
        for unit in units:
            content = unit.render()
            matched = find_patterns(content, self.patterns)
            if not matched:
                continue
            evidence.append(
                Evidence(
                    evidence_id=unit.equation_id,
                    document_id=unit.document_id,
                    target_property=target_property,
                    source_type=EvidenceType.EQUATION,
                    source_id=unit.equation_id,
                    content=content,
                    retrieval_methods=(
                        RetrievalMethod(self.name, {"matched_patterns": matched}),
                    ),
                    section=unit.section,
                    page_start=unit.page,
                    page_end=unit.page,
                )
            )
        return evidence
