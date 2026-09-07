"""Final material-property tables, joined to paper metadata without changing Facts."""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
from .review import _excel_safe

PAPER_FIELDS = (
    "paper_id",
    "doi",
    "article_title",
    "publication_name",
    "publisher",
    "year",
    "source_path",
)
FACT_FIELDS = (
    "document_id",
    *PAPER_FIELDS,
    "material_reported",
    "material_normalized",
    "property",
    "value",
    "unit",
    "qualifier",
    "conditions",
    "evidence_ids",
    "processing_issues",
)


def paper_metadata(frame=None):
    papers = {}
    if frame is None:
        return papers
    for _, row in frame.fillna("").iterrows():
        raw = row.get("metadata_json", "{}")
        try:
            extra = json.loads(raw) if isinstance(raw, str) else {}
        except (ValueError, TypeError):
            extra = {}
        if not isinstance(extra, dict):
            extra = {}
        papers[str(row["document_id"])] = {
            key: row.get(key, "") or extra.get(key, "") for key in PAPER_FIELDS
        }
    return papers


def result_rows(facts, articles=None):
    papers = paper_metadata(articles)
    rows = []
    for fact in facts:
        rows.append(
            {
                "document_id": fact.document_id,
                **{
                    key: papers.get(fact.document_id, {}).get(key, "")
                    for key in PAPER_FIELDS
                },
                "material_reported": fact.material_reported,
                "material_normalized": fact.material_normalized,
                "property": fact.property_name,
                "value": fact.fact_value.stable_value(),
                "unit": fact.fact_value.unit,
                "qualifier": fact.fact_value.qualifier or "",
                "conditions": json.dumps(fact.conditions, ensure_ascii=False),
                "evidence_ids": json.dumps(fact.evidence_ids, ensure_ascii=False),
                "processing_issues": "\n".join(fact.processing_issues),
                **{
                    f"attribute.{key}": json.dumps(value, ensure_ascii=False)
                    for key, value in fact.attributes.items()
                },
            }
        )
    return rows


def write_results_workbook(path, facts, articles=None):
    """Write final XLSX and CSV. JSON remains the lossless prediction artifact."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = result_rows(facts, articles)
    frame = pd.DataFrame(rows) if rows else pd.DataFrame(columns=FACT_FIELDS)
    frame = frame.map(_excel_safe)
    frame.to_csv(destination.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="facts", index=False)
        papers = paper_metadata(articles)
        pd.DataFrame(
            [{"document_id": key, **value} for key, value in papers.items()],
            columns=("document_id", *PAPER_FIELDS),
        ).to_excel(writer, sheet_name="papers", index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width = min(
                    65, max(16, len(str(column[0].value)) + 4)
                )
                for cell in column[1:]:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        cell.data_type = "s"
    return destination
