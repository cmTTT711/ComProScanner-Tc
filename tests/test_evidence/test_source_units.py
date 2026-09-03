from comproscanner.chunking import TextChunk
from comproscanner.evidence.source_units import (
    equation_units_from_chunks,
    table_units_from_text,
)


def test_legacy_table_block_is_preserved_verbatim():
    text = "Table 1. Curie data\nMaterial | Tc (K)\nBiFeO3 | 1103"
    units = table_units_from_text("paper_001", text)
    assert len(units) == 1
    assert units[0].render() == text


def test_equation_unit_retains_complete_nearby_original_chunk():
    content = "Composition dependence is described below.\nTc(x) = Tc0 - kx"
    chunk = TextChunk("c1", "paper_001", "results", 1, content, 8)
    units = equation_units_from_chunks([chunk])
    assert len(units) == 1
    assert units[0].equation == "Tc(x) = Tc0 - kx"
    assert units[0].nearby_text == content
