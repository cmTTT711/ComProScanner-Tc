import pandas as pd
import pytest

from comproscanner.schemas import (
    ARTICLE_CSV_COLUMNS,
    ArticleCSVSchemaError,
    normalize_legacy_article_frame,
    validate_article_frame,
)


def valid_frame():
    return pd.DataFrame(
        [{column: "" for column in ARTICLE_CSV_COLUMNS}]
    ).assign(document_id="paper_001")


def test_valid_article_frame_accepts_empty_sections():
    validate_article_frame(valid_frame())


def test_article_frame_rejects_missing_columns():
    with pytest.raises(ArticleCSVSchemaError, match="missing required columns"):
        validate_article_frame(valid_frame().drop(columns=["tables"]))


def test_article_frame_rejects_missing_document_id():
    with pytest.raises(ArticleCSVSchemaError, match="empty document_id"):
        validate_article_frame(valid_frame().assign(document_id=""))


def test_legacy_frame_is_adapted_without_rewriting_article_text():
    legacy = pd.DataFrame(
        [{"doi": "10.1000/test", "results_discussion": "Original Tc text."}]
    )
    result = normalize_legacy_article_frame(
        legacy, source_type="pdf", source_path="paper.pdf"
    )
    assert tuple(result.columns) == ARTICLE_CSV_COLUMNS
    assert result.loc[0, "document_id"] == "10.1000/test"
    assert result.loc[0, "results_discussion"] == "Original Tc text."
    validate_article_frame(result)


def test_legacy_appended_tables_are_moved_losslessly_to_tables_column():
    original = "Results paragraph.\nTable 1. Tc data\nBiFeO3 | 1103"
    result = normalize_legacy_article_frame(
        pd.DataFrame([{"doi": "10.1000/test", "results_discussion": original}])
    )
    assert result.loc[0, "results_discussion"] == "Results paragraph."
    assert result.loc[0, "tables"] == "Table 1. Tc data\nBiFeO3 | 1103"
