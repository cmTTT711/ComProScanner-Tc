"""Canonical CSV contract for PDF and publisher-XML processors."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


ARTICLE_CSV_COLUMNS = (
    "schema_version",
    "document_id",
    "paper_id",
    "doi",
    "article_title",
    "full_text",
    "abstract",
    "introduction",
    "exp_methods",
    "comp_methods",
    "results_discussion",
    "conclusion",
    "tables",
    "figures_manifest_path",
    "figure_count",
    "is_property_mentioned",
    "source_type",
    "source_path",
    "file_hash",
    "metadata_json",
)


class ArticleCSVSchemaError(ValueError):
    """Raised when an intermediate article CSV violates the canonical contract."""


def normalize_legacy_article_frame(
    frame: pd.DataFrame,
    *,
    source_type: str = "unknown",
    source_path: str = "",
) -> pd.DataFrame:
    """Adapt historical processor CSV rows to the canonical non-lossy schema.

    The adapter lets existing processors migrate independently. It adds
    provenance/default columns and losslessly moves a legacy appended table
    block into the dedicated ``tables`` field.
    """

    normalized = frame.copy()
    if "document_id" not in normalized:
        doi = normalized.get("doi", pd.Series("", index=normalized.index))
        paper = normalized.get("paper_id", pd.Series("", index=normalized.index))
        normalized["document_id"] = doi.fillna("").astype(str).str.strip()
        missing = normalized["document_id"].eq("")
        normalized.loc[missing, "document_id"] = (
            "paper_" + paper.fillna("").astype(str).str.strip().str.zfill(3)
        )[missing]
    defaults = {
        "schema_version": "1.0",
        "paper_id": "",
        "doi": "",
        "article_title": "",
        "full_text": "",
        "abstract": "",
        "introduction": "",
        "exp_methods": "",
        "comp_methods": "",
        "results_discussion": "",
        "conclusion": "",
        "tables": "",
        "figures_manifest_path": "",
        "figure_count": "0",
        "is_property_mentioned": "0",
        "source_type": source_type,
        "source_path": source_path,
        "file_hash": "",
        "metadata_json": "{}",
    }
    for column, default in defaults.items():
        if column not in normalized:
            normalized[column] = default
    section_columns = [
        "article_title", "abstract", "introduction", "exp_methods",
        "comp_methods", "results_discussion", "conclusion",
    ]
    missing_full_text = normalized["full_text"].fillna("").astype(str).str.strip().eq("")
    if missing_full_text.any():
        normalized.loc[missing_full_text, "full_text"] = normalized.loc[
            missing_full_text, section_columns
        ].fillna("").astype(str).agg("\n\n".join, axis=1).str.strip()
    for index, value in normalized["results_discussion"].fillna("").items():
        table_value = normalized.at[index, "tables"]
        if not pd.isna(table_value) and str(table_value).strip():
            continue
        marker = "\nTable 1."
        text = str(value)
        if marker in text:
            main_text, table_text = text.split(marker, 1)
            normalized.at[index, "results_discussion"] = main_text
            normalized.at[index, "tables"] = marker.lstrip("\n") + table_text
    normalized["source_type"] = normalized["source_type"].replace("", source_type)
    normalized["source_path"] = normalized["source_path"].replace("", source_path)
    return normalized.loc[:, ARTICLE_CSV_COLUMNS]


def validate_article_frame(
    frame: pd.DataFrame,
    *,
    required_columns: Iterable[str] = ARTICLE_CSV_COLUMNS,
) -> None:
    """Validate column presence and stable document identifiers.

    This deliberately does not reject empty article sections: a processor may
    legitimately be unable to recover one section. Missing columns and missing
    document identifiers are errors because they otherwise cause silent recall
    loss or make evidence impossible to trace.
    """

    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ArticleCSVSchemaError(
            "Article CSV is missing required columns: " + ", ".join(missing)
        )
    if frame.empty:
        raise ArticleCSVSchemaError("Article CSV contains no rows")
    identifiers = frame["document_id"].fillna("").astype(str).str.strip()
    if identifiers.eq("").any():
        rows = identifiers[identifiers.eq("")].index.tolist()
        raise ArticleCSVSchemaError(
            f"Article CSV has empty document_id values at rows: {rows}"
        )
