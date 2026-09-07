"""Common commands for the canonical workflow."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from comproscanner.evidence import Evidence
from comproscanner.evidence import EvidenceType
from comproscanner.evidence import RetrievalMethod
from comproscanner.results.facts import Fact
from comproscanner.results.facts import FactValue


def _default_run_id(preset: str) -> str:
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{preset}"


def _safe_file_stem(value: str) -> str:
    """Return a deterministic Windows-safe name without changing the document id."""
    invalid = '<>:"/\\|?*'
    cleaned = "".join(
        "_" if char in invalid or ord(char) < 32 else char for char in value
    )
    return cleaned.strip(" .") or "document"


def _require_network_execution(args: argparse.Namespace) -> None:
    if not args.execute_network:
        raise SystemExit(
            "Network access is disabled. Re-run with --execute-network only after "
            "explicit approval."
        )


def _load_evidence(path: Path) -> list[Evidence]:
    values = json.loads(path.read_text(encoding="utf-8"))
    return [
        Evidence(
            evidence_id=item["evidence_id"],
            document_id=item["document_id"],
            target_property=item["target_property"],
            source_type=EvidenceType(item["source_type"]),
            source_id=item["source_id"],
            content=item["content"],
            retrieval_methods=tuple(
                RetrievalMethod(method["provider"], method.get("details", {}))
                for method in item["retrieval_methods"]
            ),
            section=item.get("section"),
            page_start=item.get("page_start"),
            page_end=item.get("page_end"),
            metadata=item.get("metadata", {}),
        )
        for item in values
    ]


def _fact_from_dict(item: dict) -> Fact:
    value = item.get("fact_value") or {}
    return Fact(
        document_id=str(item["document_id"]),
        property_name=str(item["property_name"]),
        material_reported=str(item["material_reported"]),
        material_normalized=str(item["material_normalized"]),
        material_identity_key=str(item["material_identity_key"]),
        fact_value=FactValue.from_raw(
            value.get("value", ""), value.get("unit", ""), value.get("qualifier")
        ),
        evidence_ids=tuple(item.get("evidence_ids", [])),
        conditions=item.get("conditions") or {},
        material_reported_variants=tuple(item.get("material_reported_variants", [])),
        processing_issues=tuple(item.get("processing_issues", [])),
        material_resolution=tuple(item.get("material_resolution", [])),
        attributes=item.get("attributes") or {},
    )
