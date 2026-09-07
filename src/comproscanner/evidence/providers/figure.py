"""Select figures from their original caption and nearby article text."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from comproscanner.evidence.models import Evidence
from comproscanner.evidence.models import EvidenceType
from comproscanner.evidence.models import RetrievalMethod
from comproscanner.evidence.providers.base import find_patterns


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
            # Figure numbers are local to an article. Keep readable, bounded
            # path-safe labels and hash the original identities so sanitizing
            # punctuation, Unicode, or case cannot merge different sources.
            document_label = (
                re.sub(r"[^A-Za-z0-9]+", "_", unit.document_id).strip("_")[:48]
                or "document"
            )
            figure_label = (
                re.sub(r"[^A-Za-z0-9]+", "_", unit.figure_id).strip("_")[:32]
                or "figure"
            )
            identity = json.dumps(
                [unit.document_id, unit.figure_id], ensure_ascii=False
            )
            digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            evidence.append(
                Evidence(
                    evidence_id=f"{document_label}_FIGURE_{figure_label}_{digest}",
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
