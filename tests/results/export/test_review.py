import pandas as pd

from comproscanner.evidence import Evidence, EvidenceType, RetrievalMethod
from comproscanner.results.facts import Fact, FactValue
from comproscanner.results import write_review_workbook


def test_review_workbook_shows_all_original_evidence_in_one_fact_row(tmp_path):
    evidence = [
        Evidence(
            "text_1",
            "paper_001",
            "Tc",
            EvidenceType.TEXT,
            "chunk_1",
            "Original text evidence.",
            (RetrievalMethod("rule"),),
        ),
        Evidence(
            "table_1",
            "paper_001",
            "Tc",
            EvidenceType.TABLE,
            "table_1",
            "Composition | Tc (K)\nBiFeO3 | 1103",
            (RetrievalMethod("table_rule"),),
        ),
    ]
    fact = Fact(
        "paper_001",
        "Tc",
        "BiFeO3",
        "BiFeO3",
        "BiFeO3",
        FactValue.from_raw(1103, "K"),
        ("text_1", "table_1"),
    )
    path = write_review_workbook(tmp_path / "review.xlsx", [fact], evidence)
    frame = pd.read_excel(path)
    assert len(frame) == 1
    assert "Original text evidence." in frame.loc[0, "evidence"]
    assert "BiFeO3 | 1103" in frame.loc[0, "evidence"]


def test_review_workbook_removes_illegal_pdf_control_characters(tmp_path):
    evidence = [
        Evidence(
            "text_control",
            "paper_001",
            "Tc",
            EvidenceType.TEXT,
            "chunk_control",
            "Curie temperature is 698\x0e C.",
            (RetrievalMethod("rule"),),
        )
    ]
    fact = Fact(
        "paper_001",
        "Tc",
        "sample",
        "sample",
        "sample",
        FactValue.from_raw(698, "C"),
        ("text_control",),
    )

    path = write_review_workbook(tmp_path / "review.xlsx", [fact], evidence)
    frame = pd.read_excel(path)
    assert "\x0e" not in frame.loc[0, "evidence"]
    assert "698 C" in frame.loc[0, "evidence"]


def test_review_workbook_shows_normalization_and_validation_issues(tmp_path):
    fact = Fact(
        "paper_001",
        "Tc",
        "BFO sample",
        "BFO sample",
        "BFO sample",
        FactValue.from_raw(1103, "K"),
        ("text_1",),
        processing_issues=(
            "material_normalization_failed: HTTP 503",
            "missing_condition: method",
        ),
    )
    path = write_review_workbook(tmp_path / "review.xlsx", [fact], [])
    frame = pd.read_excel(path)
    assert frame.loc[0, "material_reported"] == "BFO sample"
    assert frame.loc[0, "value"] == 1103
    assert (
        frame.loc[0, "processing_issues"]
        == "material_normalization_failed: HTTP 503\nmissing_condition: method"
    )
