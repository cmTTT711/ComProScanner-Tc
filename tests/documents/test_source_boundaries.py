"""Exercise real local publisher input without discovery or model calls."""

from pathlib import Path
import importlib
import hashlib
import zipfile
from unittest.mock import Mock

from lxml import etree
import pandas as pd
import pytest

from comproscanner.presets import get_preset


@pytest.mark.parametrize(
    "publisher,typename,section_tag,paragraph_tag",
    [
        ("elsevier", "ElsevierArticleProcessor", "section", "para"),
        ("springer", "SpringerArticleProcessor", "sec", "p"),
        ("iop", "IOPArticleProcessor", "sec", "p"),
    ],
)
def test_unfamiliar_sections_and_tc_pattern_dict_survive(
    publisher, typename, section_tag, paragraph_tag
):
    from comproscanner.documents.config import ArticleRelatedKeywords

    cls = getattr(
        importlib.import_module(
            f"comproscanner.documents.publishers.{publisher}_processor"
        ),
        typename,
    )
    processor = cls.__new__(cls)
    processor.property_keywords = get_preset("curie_temperature").property_keywords
    processor.article_related_keywords = ArticleRelatedKeywords()
    sections = [
        etree.fromstring(
            f"<{section_tag}><title>Unusual heading</title><{paragraph_tag}>BaTiO3 Curie temperature is 393 K.</{paragraph_tag}></{section_tag}>"
        )
    ]
    frame = processor._append_sections_to_df(
        [], sections, "10.test/p", None, "Title", "Journal", publisher
    )
    assert "BaTiO3 Curie temperature is 393 K." in frame.iloc[0].full_text


def test_iop_local_xml_needs_no_metadata_and_preserves_originals(tmp_path, monkeypatch):
    from comproscanner.documents.publishers.iop_processor import IOPArticleProcessor

    original = tmp_path / "originals"
    original.mkdir()
    xml = b'<article><front><article-meta><article-id pub-id-type="doi">10.1088/test_sample</article-id><title-group><article-title>Local test</article-title></title-group></article-meta></front><body><sec><title>Results</title><p>BaTiO3 Curie temperature is 393 K.</p></sec></body></article>'
    (original / "unrelated-filename.xml").write_bytes(xml)
    with zipfile.ZipFile(original / "assets.zip", "w") as archive:
        archive.writestr("image.bin", b"original picture bytes")
    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in original.iterdir()
    }
    monkeypatch.setenv("IOP_papers_path", str(original))
    processor = IOPArticleProcessor(
        "curie_temperature", get_preset("curie_temperature").property_keywords
    )
    processor.process_iop_articles()
    assert {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in original.iterdir()
    } == before
    frame = pd.read_csv(processor.csv_filepath)
    assert frame.iloc[0].doi == "10.1088/test_sample"
    assert "393 K" in frame.iloc[0].full_text
    assert processor.prepare_iop_files.get_all_iop_dois() == ["10.1088/test_sample"]
    assert (
        Path(processor.iop_folderpath) / "archive_assets/assets/image.bin"
    ).read_bytes() == b"original picture bytes"
    assert (
        processor._download_iop_figure_from_content_cdn(
            "a", "b", "c", "d", "figure.png", "key"
        )
        is None
    )


def test_unlabeled_dois_are_tried_by_selected_publishers(monkeypatch):
    from comproscanner.documents.dispatch import ArticleProcessor

    pd.DataFrame([{"doi": "10.test/a", "general_publisher": ""}]).to_csv(
        "results/tc_metadata.csv", index=False
    )
    factories = []
    for module, name in [
        ("elsevier", "ElsevierArticleProcessor"),
        ("springer", "SpringerArticleProcessor"),
    ]:
        factory = Mock()
        monkeypatch.setattr(
            importlib.import_module(
                f"comproscanner.documents.publishers.{module}_processor"
            ),
            name,
            factory,
        )
        factories.append(factory)
    ArticleProcessor("tc").process_articles(
        property_keywords={},
        source_list=["elsevier", "springer"],
        doi_list=["10.test/a"],
    )
    assert all(
        factory.call_args.kwargs["doi_list"] == ["10.test/a"] for factory in factories
    )


def test_disabled_figure_tool_does_not_open_manifest(tmp_path):
    from comproscanner.evidence.preparation import EvidencePreparationPipeline

    bad = tmp_path / "malformed.json"
    bad.write_text("not json", encoding="utf-8")
    pipeline = EvidencePreparationPipeline(
        target_property="band gap",
        property_keywords={"exact_keywords": ["band gap"]},
        provider_names=("rule_text",),
    )
    _, evidence = pipeline.prepare_all(
        {
            "document_id": "p1",
            "full_text": "GaN band gap is 3.4 eV.",
            "figures_manifest_path": str(bad),
        }
    )
    assert len(evidence) == 1


def test_csv_failure_is_reported_to_document_stage(tmp_path, monkeypatch):
    from comproscanner.documents.csv_store import ArticleCSVStore

    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail)
    with pytest.raises(OSError, match="disk full"):
        ArticleCSVStore().write_to_csv(
            pd.DataFrame(
                [{"document_id": "p1", "doi": "10.test/a", "full_text": "body"}]
            ),
            str(tmp_path / "csv"),
            "tc",
            "test",
            1,
        )
