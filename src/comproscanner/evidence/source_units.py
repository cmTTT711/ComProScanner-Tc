"""Adapters from canonical CSV sidecars to non-text Evidence source units."""

from __future__ import annotations

import re
from pathlib import Path
from comproscanner._paths import resolve_recorded_path

from comproscanner.evidence.chunking import TextChunk
from comproscanner.evidence.figure_manifest import load_figure_units
from comproscanner.evidence.providers.equation import EquationUnit
from comproscanner.evidence.providers.table import TableUnit

_TABLE_START = re.compile(r"(?im)(?=^\s*(?:table|tab\.)\s*\d+[A-Za-z]?[.:])")
_EQUATION = re.compile(
    r"(?m)(?:^|(?<=\n))\s*([^\n]{0,180}(?:T\s*_?\s*[cC]|[A-Za-z]\w*(?:\([^\n)]*\))?)\s*=\s*[^\n]{1,220})"
)


def table_units_from_text(document_id: str, text: str) -> list[TableUnit]:
    """Preserve legacy extracted table blocks until structured cells are available."""

    value = str(text or "").strip()
    if not value:
        return []
    blocks = [block.strip() for block in _TABLE_START.split(value) if block.strip()]
    return [
        TableUnit(
            table_id=f"{document_id.replace('/', '_')}_TABLE_{index:04d}",
            document_id=document_id,
            caption=block.splitlines()[0],
            headers=(),
            rows=(),
            raw_content=block,
        )
        for index, block in enumerate(blocks, start=1)
    ]


def equation_units_from_chunks(chunks: list[TextChunk]) -> list[EquationUnit]:
    """Find explicit equations while retaining their complete source chunk."""

    units = []
    for chunk in chunks:
        for index, match in enumerate(_EQUATION.finditer(chunk.content), start=1):
            units.append(
                EquationUnit(
                    equation_id=f"{chunk.chunk_id}_EQ_{index:02d}",
                    document_id=chunk.document_id,
                    equation=match.group(1).strip(),
                    nearby_text=chunk.content,
                    section=chunk.section,
                    page=chunk.page_start,
                )
            )
    return units


def figure_units_from_manifest(path: str) -> list:
    value = str(path or "").strip()
    if not value or not resolve_recorded_path(value).is_file():
        return []
    return load_figure_units(value)
