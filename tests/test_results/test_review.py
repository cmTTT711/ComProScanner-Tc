import pandas as pd

from comproscanner.evidence import Evidence, EvidenceType, RetrievalMethod
from comproscanner.facts import Fact, FactValue
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
