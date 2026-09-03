import json

from comproscanner.evidence.figure_manifest import load_figure_units
from comproscanner.utils.figure_extractor import FigureExtractor


def test_figure_manifest_keeps_original_caption_and_image_path(tmp_path):
    manifest = FigureExtractor.update_manifest(
        "paper_001", "Fig 1", "Original Curie plot caption", str(tmp_path), page=4
    )
    units = load_figure_units(manifest)
    assert len(units) == 1
    assert units[0].caption == "Original Curie plot caption"
    assert units[0].page == 4
    assert units[0].image_path.endswith("Fig_1.jpg")
