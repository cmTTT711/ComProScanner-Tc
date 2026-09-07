"""Human review workbook with original Evidence visible beside every Fact."""

from __future__ import annotations

from copy import copy
import json
from openpyxl.worksheet.datavalidation import DataValidation
from pathlib import Path
from comproscanner._paths import resolve_recorded_path

import pandas as pd
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from comproscanner.evidence import Evidence
from comproscanner.results.facts import Fact


def _excel_safe(value):
    """Remove XML control characters that XLSX cells cannot represent."""

    return ILLEGAL_CHARACTERS_RE.sub("", value) if isinstance(value, str) else value


def _evidence_text(item: Evidence) -> str:
    location = " | ".join(
        value
        for value in (
            item.source_type.value,
            item.section or "",
            f"p.{item.page_start}" if item.page_start is not None else "",
            "+".join(method.provider for method in item.retrieval_methods),
        )
        if value
    )
    image_path = item.metadata.get("image_path")
    image_line = f"\n[image] {resolve_recorded_path(image_path)}" if image_path else ""
    return f"[{location}]\n{item.content}{image_line}"


def write_review_workbook(
    path: str | Path, facts: list[Fact], evidence: list[Evidence]
) -> Path:
    """Write one Fact per row and combine all supporting source text in one cell."""

    evidence_by_id = {item.evidence_id: item for item in evidence}
    rows = []
    for fact in facts:
        supporting = [
            evidence_by_id[evidence_id]
            for evidence_id in fact.evidence_ids
            if evidence_id in evidence_by_id
        ]
        rows.append(
            {
                "document_id": fact.document_id,
                "material_reported": fact.material_reported,
                "material_reported_variants": "\n".join(
                    fact.material_reported_variants or (fact.material_reported,)
                ),
                "material_normalized": fact.material_normalized,
                "property": fact.property_name,
                "value": fact.fact_value.stable_value(),
                "qualifier": fact.fact_value.qualifier or "",
                "unit": fact.fact_value.unit,
                "conditions": str(fact.conditions) if fact.conditions else "",
                "processing_issues": "\n".join(fact.processing_issues),
                "evidence": "\n\n---\n\n".join(map(_evidence_text, supporting)),
                "decision": "",
                "review_note": "",
                **(
                    {
                        "material_resolution": json.dumps(
                            fact.material_resolution, ensure_ascii=False
                        )
                    }
                    if fact.material_resolution
                    else {}
                ),
                "evidence_ids": json.dumps(fact.evidence_ids, ensure_ascii=False),
                **(
                    {"attributes": json.dumps(fact.attributes, ensure_ascii=False)}
                    if fact.attributes
                    else {}
                ),
            }
        )
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows).map(_excel_safe)
    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="facts", index=False)
        sheet = writer.sheets["facts"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        decisions = DataValidation(
            type="list", formula1='"ACCEPT,REJECT,MODIFY"', allow_blank=True
        )
        sheet.add_data_validation(decisions)
        if rows:
            decisions.add(f"L2:L{len(rows)+1}")
        widths = {
            "A": 22,
            "B": 32,
            "C": 38,
            "D": 32,
            "E": 18,
            "F": 14,
            "G": 14,
            "H": 12,
            "I": 28,
            "J": 45,
            "K": 90,
            "L": 14,
            "M": 30,
            "N": 85,
        }
        for column, width in widths.items():
            sheet.column_dimensions[column].width = width
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                alignment = copy(cell.alignment)
                alignment.vertical = "top"
                alignment.wrap_text = True
                cell.alignment = alignment
    return destination
