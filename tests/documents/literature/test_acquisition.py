import json
from unittest.mock import Mock

import pymupdf
import pytest

from comproscanner.documents.literature.acquisition import acquire_pdfs, merge_candidates, verify_pdf


def test_aps_download_preserves_publisher_path_case():
    from comproscanner.documents.literature.acquisition import _fill_publisher
    row = {"doi": "10.1103/physrevlett.125.247601", "publisher": "American Physical Society"}
    response = Mock()
    response.json.return_value = {"message": {
        "DOI": row["doi"], "publisher": "American Physical Society (APS)",
        "resource": {"primary": {"URL": "https://link.aps.org/doi/10.1103/PhysRevLett.125.247601"}},
    }}
    session = Mock()
    session.get.return_value = response
    _fill_publisher(row, session)
    assert row["doi"] == "10.1103/physrevlett.125.247601"
    assert row["download_doi"] == "10.1103/PhysRevLett.125.247601"


def pdf(path, text):
    doc = pymupdf.open()
    doc.new_page().insert_text((40, 50), text)
    doc.save(path)
    doc.close()


def test_merge_uses_doi_and_preserves_both_sources():
    rows = merge_candidates(
        [{"doi": "https://doi.org/10.1/A", "discovery_source": "scopus"}],
        [{"doi": "10.1/a", "discovery_source": "openalex", "publisher": "APS"}],
    )
    assert len(rows) == 1
    assert rows[0]["discovery_sources"] == ["scopus", "openalex"]
    assert rows[0]["publisher"] == "APS"


def test_reference_doi_does_not_verify_wrong_article(tmp_path):
    path = tmp_path / "wrong.pdf"
    doc = pymupdf.open()
    for text in ("Unrelated article", "Unrelated methods", "References 10.1/target"):
        doc.new_page().insert_text((40, 50), text)
    doc.save(path)
    doc.close()
    assert not verify_pdf(path, {"doi": "10.1/target"})["verified"]


def test_acs_navigation_label_is_not_a_supplement(tmp_path):
    path = tmp_path / "acs.pdf"
    pdf(path, "Full article title\n" + ("Author affiliation and publication details\n" * 5) + "Supporting Information\nABSTRACT: 10.1/test")
    assert verify_pdf(path, {"doi": "10.1/test"})["verified"]
    supplement = tmp_path / "supplement.pdf"
    pdf(supplement, "Supporting Information\n10.1/test")
    assert not verify_pdf(supplement, {"doi": "10.1/test"})["verified"]


def test_resume_and_browser_import_do_not_download(tmp_path):
    source = tmp_path / "browser.pdf"
    pdf(source, "10.1/test\nA multiferroic material with strong magnetoelectric coupling")
    manifest = tmp_path / "browser.json"
    manifest.write_text(json.dumps({"results": [{"doi": "10.1/test", "pdf_path": str(source)}]}))
    session = Mock()
    rows = [{"doi": "10.1/test", "publisher": "APS"}]
    result = acquire_pdfs(rows, tmp_path / "run", api_key="", session=session, browser_manifest=manifest)
    assert result["status_counts"] == {"downloaded": 1}
    result = acquire_pdfs(rows, tmp_path / "run", api_key="", session=session)
    assert result["status_counts"] == {"downloaded": 1}
    session.get.assert_not_called()
    with pytest.raises(ValueError, match="DOI list changed"):
        acquire_pdfs([{"doi": "10.1/other"}], tmp_path / "run", api_key="", session=session)


def test_nature_unedited_cover_is_not_article_and_is_quarantined(tmp_path):
    import hashlib
    root = tmp_path / "run"
    folder = root / "pdfs"
    folder.mkdir(parents=True)
    path = folder / (hashlib.sha256(b"10.1/test").hexdigest()[:20] + ".pdf")
    pdf(path, "nature electronics\n10.1/test\nArticle\nExample title\nIn the format provided by the\nauthors and unedited")
    assert not verify_pdf(path, {"doi": "10.1/test"})["verified"]
    manifest = tmp_path / "empty.json"
    manifest.write_text("[]")
    session = Mock()
    result = acquire_pdfs([{"doi": "10.1/test"}], root, api_key="", session=session, browser_manifest=manifest)
    assert result["status_counts"] == {"unverified": 1}
    assert not path.exists()
    assert (root / "quarantine" / path.name).exists()
    session.get.assert_not_called()


def test_public_failure_falls_back_to_archive_and_budget_is_resumable(tmp_path, monkeypatch):
    from comproscanner.documents.literature import acquisition

    response = Mock()
    response.json.return_value = {
        "doi": "10.1/test", "id": "https://openalex.org/W1",
        "locations": [{"is_oa": True, "pdf_url": "https://example.org/p.pdf"}],
        "content_urls": {"pdf": "https://content.openalex.org/works/W1.pdf"},
    }
    session = Mock()
    session.get.return_value = response
    calls = []

    def download(url, path, **kwargs):
        calls.append(url)
        if "example.org" in url:
            raise ValueError("not a pdf")
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf(path, "10.1/test")
        return "hash", 10000

    monkeypatch.setattr(acquisition, "download_validated_pdf", download)
    rows = [{"doi": "10.1/test"}]
    result = acquire_pdfs(rows, tmp_path, api_key="secret", max_archive_requests=0, session=session)
    assert result["status_counts"] == {"needs_browser": 1}
    result = acquire_pdfs(rows, tmp_path, api_key="secret", max_archive_requests=1, session=session)
    assert result["download_sources"] == {"openalex_archive": 1}
    assert result["archive_requests_reserved"] == 1
    assert len(calls) == 2
    assert "secret" not in (tmp_path / "manifest.json").read_text()
