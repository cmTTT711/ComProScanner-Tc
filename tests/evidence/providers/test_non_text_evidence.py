from comproscanner.evidence.providers.equation import (
    EquationEvidenceProvider,
    EquationUnit,
)
from comproscanner.evidence.providers.figure import FigureEvidenceProvider, FigureUnit
from comproscanner.evidence.providers.table import TableEvidenceProvider, TableUnit


def test_table_evidence_keeps_caption_headers_rows_and_footnotes():
    unit = TableUnit(
        table_id="P001_TABLE_001",
        document_id="paper_001",
        caption="Reported Curie temperature",
        headers=("Composition", "Tc (K)"),
        rows=(("BiFeO3", "1103"),),
        footnotes=("Measured during heating",),
        page=5,
    )
    evidence = TableEvidenceProvider((r"\bTc\b",)).select([unit], "tc")
    assert len(evidence) == 1
    assert "Composition | Tc (K)" in evidence[0].content
    assert "BiFeO3 | 1103" in evidence[0].content
    assert "Measured during heating" in evidence[0].content


def test_figure_evidence_preserves_image_reference_and_original_caption():
    unit = FigureUnit(
        figure_id="P001_FIGURE_001",
        document_id="paper_001",
        image_path="figures/fig_001.jpg",
        caption="Temperature dependence of permittivity near the Curie point",
    )
    evidence = FigureEvidenceProvider((r"Curie",)).select([unit], "tc")
    assert len(evidence) == 1
    assert evidence[0].metadata["image_path"] == "figures/fig_001.jpg"
    assert evidence[0].content == unit.caption


def test_equation_evidence_keeps_equation_and_nearby_original_text():
    unit = EquationUnit(
        equation_id="P001_EQ_001",
        document_id="paper_001",
        equation="Tc(x) = Tc0 - kx",
        nearby_text="The Curie temperature decreases with substitution.",
    )
    evidence = EquationEvidenceProvider((r"Curie|Tc",)).select([unit], "tc")
    assert len(evidence) == 1
    assert "Tc(x) = Tc0 - kx" in evidence[0].content
    assert "decreases with substitution" in evidence[0].content
