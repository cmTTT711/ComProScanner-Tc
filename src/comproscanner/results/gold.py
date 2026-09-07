"""Import explicitly accepted review rows into a new Gold file."""

import ast
import json
from pathlib import Path

import pandas as pd
from .evaluation import score_exact_facts


def accept_review(review, output):
    destination = Path(output)
    if destination.exists():
        raise FileExistsError("Gold already exists; choose a new output file")
    frame = pd.read_excel(review, sheet_name="facts", dtype=str).fillna("")
    required = {
        "decision",
        "document_id",
        "material_normalized",
        "property",
        "value",
        "unit",
        "evidence_ids",
    }
    if not required <= set(frame.columns):
        raise ValueError(
            "Review is missing required fields: "
            + ", ".join(sorted(required - set(frame.columns)))
        )
    records = []
    for index, row in frame.iterrows():
        decision = row["decision"].strip().upper()
        if decision in {"", "REJECT"}:
            continue
        if decision not in {"ACCEPT", "MODIFY"}:
            raise ValueError(f"Review row {index+2}: invalid decision {decision}")
        raw = row.get("conditions", "")
        # Read both the historical Python-dict cells and current JSON cells.
        try:
            conditions = json.loads(raw) if raw else {}
        except ValueError:
            conditions = ast.literal_eval(raw)
        evidence_ids = json.loads(row["evidence_ids"])
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise ValueError(f"Review row {index+2}: missing supporting Evidence IDs")
        record = {
            "document_id": row["document_id"],
            "material": row["material_normalized"],
            "property": row["property"],
            "value": row["value"],
            "unit": row["unit"],
            "qualifier": row.get("qualifier") or None,
            "conditions": conditions,
            "evidence_ids": evidence_ids,
            "strict_scoring": True,
            "gold_status": "ACCEPTED",
            "review_decision": decision,
            "review_note": row.get("review_note", ""),
        }
        if row.get("attributes"):
            record["attributes"] = json.loads(row["attributes"])
        records.append(record)
    if not records:
        raise ValueError("Review contains no ACCEPT or MODIFY rows")
    score_exact_facts(records, [])  # Validate before creating any Gold output.
    content = json.dumps(records, ensure_ascii=False, indent=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(content)
    return destination
