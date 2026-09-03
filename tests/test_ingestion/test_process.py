from unittest.mock import MagicMock

import pytest

from comproscanner.ingestion.process import (
    build_processing_plan,
    execute_processing_plan,
    read_doi_file,
)


def test_local_pdf_plan_is_offline_and_maps_to_legacy_processor(tmp_path):
    plan = build_processing_plan(
        preset="curie_temperature",
        sources=["manual_pdf"],
        folder_path=tmp_path,
        execute_network=False,
    )

    assert plan.processor_sources == ("pdfs",)
    assert plan.network_required is False
    assert plan.metadata_network_allowed is False
    assert plan.folder_path == str(tmp_path.resolve())


def test_local_pdf_sources_must_be_processed_separately(tmp_path):
    with pytest.raises(ValueError, match="separately"):
        build_processing_plan(
            preset="curie_temperature",
            sources=["manual_pdf", "downloaded_pdf"],
            folder_path=tmp_path,
        )


def test_springer_tdm_key_is_optional(monkeypatch):
    monkeypatch.setenv("SPRINGER_OPENACCESS_API_KEY", "present")
    monkeypatch.delenv("SPRINGER_TDM_API_KEY", raising=False)

    plan = build_processing_plan(
        preset="curie_temperature",
        sources=["springer"],
        execute_network=True,
    )

    assert plan.missing_credentials == ()
    assert plan.optional_credentials_absent == ("SPRINGER_TDM_API_KEY",)


def test_execute_forwards_plan_without_importing_real_scanner(tmp_path):
    factory = MagicMock()
    plan = build_processing_plan(
        preset="curie_temperature",
        sources=["manual_pdf"],
        folder_path=tmp_path,
    )

    execute_processing_plan(
        plan,
        main_property_keyword="ferroelectric",
        property_keywords={"exact_keywords": ["Tc"]},
        processing_kwargs={"allow_missing_doi": True},
        scanner_factory=factory,
    )

    factory.assert_called_once_with(main_property_keyword="ferroelectric")
    kwargs = factory.return_value.process_articles.call_args.kwargs
    assert kwargs["source_list"] == ["pdfs"]
    assert kwargs["allow_missing_doi"] is True
    assert kwargs["allow_metadata_network"] is False


def test_read_doi_file_normalizes_url_and_deduplicates(tmp_path):
    source = tmp_path / "dois.txt"
    source.write_text(
        "# comment\nhttps://doi.org/10.1/one\n10.1/one\n10.2/two\n",
        encoding="utf-8",
    )
    assert read_doi_file(source) == ["10.1/one", "10.2/two"]
