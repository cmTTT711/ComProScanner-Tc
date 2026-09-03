"""Select figures from their original caption and nearby article text."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Evidence, EvidenceType, RetrievalMethod
from .base import find_patterns


@dataclass(frozen=True)
class FigureUnit:
    figure_id: str
    document_id: str
    image_path: str
    caption: str
    nearby_text: str = ""
    section: str | None = None
    page: int | None = None

    def render(self) -> str:
        return f"{self.caption}\n{self.nearby_text}".strip()


class FigureEvidenceProvider:
    name = "figure_caption_rule"

    def __init__(self, patterns: tuple[str, ...]):
        self.patterns = patterns

    def select(self, units: list[FigureUnit], target_property: str) -> list[Evidence]:
        evidence: list[Evidence] = []
        for unit in units:
            content = unit.render()
            matched = find_patterns(content, self.patterns)
            if not matched:
                continue
            evidence.append(
                Evidence(
                    evidence_id=unit.figure_id,
                    document_id=unit.document_id,
                    target_property=target_property,
                    source_type=EvidenceType.FIGURE,
                    source_id=unit.figure_id,
                    content=content,
                    retrieval_methods=(
                        RetrievalMethod(self.name, {"matched_patterns": matched}),
                    ),
                    section=unit.section,
                    page_start=unit.page,
                    page_end=unit.page,
                    metadata={"image_path": unit.image_path},
                )
            )
        return evidence
