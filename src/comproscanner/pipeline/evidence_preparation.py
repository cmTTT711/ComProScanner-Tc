"""Prepare canonical text evidence from one standard article row."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..chunking import TextChunkConfig, TextChunker
from ..evidence import Evidence, TextEvidenceBuilder
from ..evidence.providers import RuleTextEvidenceProvider
from ..evidence.providers import (
    EquationEvidenceProvider,
    FigureEvidenceProvider,
    TableEvidenceProvider,
)
from ..evidence.source_units import (
    equation_units_from_chunks,
    figure_units_from_manifest,
    table_units_from_text,
)
from ..evidence.text import TextChunkMatch


TEXT_SECTIONS = (
    "article_title",
    "abstract",
    "introduction",
    "exp_methods",
    "comp_methods",
    "results_discussion",
    "conclusion",
)


def preset_patterns(property_keywords: dict) -> tuple[str, ...]:
    """Convert the existing property-keyword shape into regex patterns."""

    patterns = [
        item["pattern"]
        for item in property_keywords.get("candidate_patterns", [])
        if item.get("pattern")
    ]
    patterns.extend(
        rf"(?<!\w){re.escape(keyword)}(?!\w)"
        for keyword in property_keywords.get("exact_keywords", [])
        if keyword
    )
    patterns.extend(
        re.escape(keyword)
        for keyword in property_keywords.get("substring_keywords", [])
        if keyword
    )
    patterns.extend(property_keywords.get("regex_keywords", []))
    return tuple(dict.fromkeys(patterns))


class EvidencePreparationPipeline:
    """Generate source-preserving evidence without calling an external LLM."""

    def __init__(
        self,
        *,
        target_property: str,
        property_keywords: dict,
        rule_patterns: Iterable[str] | None = None,
        chunk_config: TextChunkConfig | None = None,
    ):
        self.target_property = target_property
        self.chunker = TextChunker(chunk_config)
        self.rule_provider = RuleTextEvidenceProvider(
            tuple(rule_patterns or ()) or preset_patterns(property_keywords)
        )
        source_patterns = preset_patterns(property_keywords)
        self.table_provider = TableEvidenceProvider(source_patterns)
        self.figure_provider = FigureEvidenceProvider(source_patterns)
        self.equation_provider = EquationEvidenceProvider(source_patterns)
        self.builder = TextEvidenceBuilder()

    def prepare_text(
        self,
        row,
        *,
        vector_matches: Iterable[TextChunkMatch] = (),
    ) -> tuple[list, list[Evidence]]:
        document_id = str(row["document_id"])
        sections = {}
        for section in TEXT_SECTIONS:
            value = row.get(section, "")
            sections[section] = "" if value is None or str(value) == "nan" else str(value)
        chunks = self.chunker.split_article(document_id, sections)
        matches = [*self.rule_provider.select(chunks), *vector_matches]
        return chunks, self.builder.build(
            chunks=chunks,
            matches=matches,
            target_property=self.target_property,
        )

    def prepare_all(
        self,
        row,
        *,
        vector_matches: Iterable[TextChunkMatch] = (),
    ) -> tuple[list, list[Evidence]]:
        """Prepare text, table, figure-caption, and equation Evidence locally."""

        chunks, text_evidence = self.prepare_text(
            row, vector_matches=vector_matches
        )
        document_id = str(row["document_id"])
        tables = table_units_from_text(document_id, row.get("tables", ""))
        equations = equation_units_from_chunks(chunks)
        figures = figure_units_from_manifest(row.get("figures_manifest_path", ""))
        evidence = [
            *text_evidence,
            *self.table_provider.select(tables, self.target_property),
            *self.figure_provider.select(figures, self.target_property),
            *self.equation_provider.select(equations, self.target_property),
        ]
        return chunks, evidence
