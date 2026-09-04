"""Prepare canonical text evidence from one standard article row."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..chunking import TextChunkConfig, TextChunker
from ..evidence import Evidence, EvidenceProviderRegistry, TextEvidenceBuilder
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

_REFERENCE_HEADING = re.compile(
    r"(?im)^[ \t]*#{1,6}[ \t]+(?:references|bibliography|参考文献)[ \t]*$"
)


def split_reference_region(text: str) -> dict[str, str]:
    """Mark a likely terminal bibliography without discarding source text."""

    matches = list(_REFERENCE_HEADING.finditer(text))
    for match in reversed(matches):
        # Multi-column parsing can place a references column early. Prefer
        # recall in that ambiguous case and keep the heading in normal text.
        if match.start() < len(text) * 0.55:
            continue
        return {
            "full_text": text[: match.start()].rstrip(),
            "references": text[match.start() :].lstrip(),
        }
    return {"full_text": text}


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
        provider_names: Iterable[str] | None = None,
        provider_registry: EvidenceProviderRegistry | None = None,
    ):
        self.target_property = target_property
        self.chunker = TextChunker(chunk_config)
        self.provider_names = tuple(
            dict.fromkeys(
                name.strip().casefold()
                for name in (provider_names or ("rule_text", "table", "figure", "equation"))
            )
        )
        source_patterns = preset_patterns(property_keywords)
        rule_patterns = tuple(rule_patterns or ()) or source_patterns
        registry = provider_registry or EvidenceProviderRegistry()
        if provider_registry is None:
            registry.register("rule_text", lambda: RuleTextEvidenceProvider(rule_patterns))
            registry.register("table", lambda: TableEvidenceProvider(source_patterns))
            registry.register("figure", lambda: FigureEvidenceProvider(source_patterns))
            registry.register("equation", lambda: EquationEvidenceProvider(source_patterns))
        supported = set(registry.names()) | {"physbert"}
        unknown = sorted(set(self.provider_names) - supported)
        if unknown:
            raise ValueError("Unknown Evidence provider(s): " + ", ".join(unknown))
        self.rule_provider = (
            registry.create("rule_text") if "rule_text" in self.provider_names else None
        )
        self.table_provider = (
            registry.create("table") if "table" in self.provider_names else None
        )
        self.figure_provider = (
            registry.create("figure") if "figure" in self.provider_names else None
        )
        self.equation_provider = (
            registry.create("equation") if "equation" in self.provider_names else None
        )
        self.builder = TextEvidenceBuilder()

    def prepare_text(
        self,
        row,
        *,
        vector_matches: Iterable[TextChunkMatch] = (),
    ) -> tuple[list, list[Evidence]]:
        document_id = str(row["document_id"])
        full_text = row.get("full_text", "")
        full_text = "" if full_text is None or str(full_text) == "nan" else str(full_text)
        if full_text.strip():
            sections = split_reference_region(full_text)
        else:
            sections = {}
            for section in TEXT_SECTIONS:
                value = row.get(section, "")
                sections[section] = "" if value is None or str(value) == "nan" else str(value)
        chunks = self.chunker.split_article(document_id, sections)
        searchable_chunks = [chunk for chunk in chunks if chunk.section != "references"]
        rule_matches = (
            self.rule_provider.select(searchable_chunks) if self.rule_provider else []
        )
        matches = [*rule_matches, *vector_matches]
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
        equations = equation_units_from_chunks(
            chunk for chunk in chunks if chunk.section != "references"
        )
        figures = figure_units_from_manifest(row.get("figures_manifest_path", ""))
        evidence = [*text_evidence]
        if self.table_provider:
            evidence.extend(self.table_provider.select(tables, self.target_property))
        if self.figure_provider:
            evidence.extend(self.figure_provider.select(figures, self.target_property))
        if self.equation_provider:
            evidence.extend(self.equation_provider.select(equations, self.target_property))
        return chunks, evidence
