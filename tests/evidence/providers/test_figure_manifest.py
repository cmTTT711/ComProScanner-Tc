import json

from comproscanner.evidence.figure_manifest import load_figure_units
from comproscanner.documents.figures import FigureExtractor


def test_figure_manifest_keeps_original_caption_and_image_path(tmp_path):
    manifest = FigureExtractor.update_manifest(
        "paper_001", "Fig 1", "Original Curie plot caption", str(tmp_path), page=4
    )
    units = load_figure_units(manifest)
    assert len(units) == 1
    assert units[0].caption == "Original Curie plot caption"
    assert units[0].page == 4
    assert units[0].image_path.endswith("Fig_1.jpg")


def _write_manifest(directory, image_path):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "document_id": "paper_001",
                "figures": [
                    {
                        "figure_id": "figure_0",
                        "path": str(image_path),
                        "caption": "Original caption",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_historical_workspace_relative_figure_path_resolves_to_article_sibling(
    tmp_path,
):
    article_dir = tmp_path / "results" / "related_figures" / "paper_001"
    manifest = _write_manifest(
        article_dir, "results/related_figures/paper_001/figure_0.jpg"
    )
    image = article_dir / "figure_0.jpg"
    image.write_bytes(b"original article image")

    unit = load_figure_units(manifest)[0]

    assert unit.image_path == str(image)
    assert unit.caption == "Original caption"


def test_existing_manifest_relative_path_takes_precedence_over_sibling(tmp_path):
    article_dir = tmp_path / "paper_001"
    manifest = _write_manifest(article_dir, "images/paper_001/figure_0.jpg")
    image = article_dir / "images" / "paper_001" / "figure_0.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"explicit image")
    (article_dir / "figure_0.jpg").write_bytes(b"other sibling image")

    assert load_figure_units(manifest)[0].image_path == str(image)


def test_absolute_figure_path_is_preserved_even_when_missing(tmp_path):
    image = tmp_path / "elsewhere" / "figure_0.jpg"
    manifest = _write_manifest(tmp_path / "paper_001", image)
    (manifest.parent / "figure_0.jpg").write_bytes(b"other sibling image")

    assert load_figure_units(manifest)[0].image_path == str(image)


def test_historical_fallback_does_not_substitute_another_articles_image(tmp_path):
    article_dir = tmp_path / "paper_001"
    stored = "results/related_figures/paper_002/figure_0.jpg"
    manifest = _write_manifest(article_dir, stored)
    (article_dir / "figure_0.jpg").write_bytes(b"wrong article image")

    assert load_figure_units(manifest)[0].image_path == str(article_dir / stored)


def test_missing_historical_image_retains_original_resolution(tmp_path):
    article_dir = tmp_path / "paper_001"
    stored = "results/related_figures/paper_001/figure_0.jpg"
    manifest = _write_manifest(article_dir, stored)

    assert load_figure_units(manifest)[0].image_path == str(article_dir / stored)
