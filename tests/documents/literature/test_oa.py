from unittest.mock import Mock

import pytest

from comproscanner.documents.literature import (
    download_validated_pdf,
    resolve_openalex_urls,
)


def _response(chunks):
    response = Mock()
    response.iter_content.return_value = chunks
    response.raise_for_status.return_value = None
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return response


def test_openalex_returns_unique_pdf_urls():
    response = Mock(status_code=200)
    response.json.return_value = {
        "best_oa_location": {"pdf_url": "https://example/a.pdf"},
        "locations": [
            {"pdf_url": "https://example/a.pdf"},
            {"pdf_url": "https://example/b.pdf"},
        ],
    }
    response.raise_for_status.return_value = None
    session = Mock()
    session.get.return_value = response
    assert resolve_openalex_urls("10.1/A", session=session) == [
        "https://example/a.pdf",
        "https://example/b.pdf",
    ]


def test_download_rejects_html_and_removes_partial_file(tmp_path):
    session = Mock()
    session.get.return_value = _response([b"<html>not a pdf</html>" * 1000])
    destination = tmp_path / "paper.pdf.part"
    with pytest.raises(ValueError, match="not a PDF"):
        download_validated_pdf(
            "https://example/paper", destination, session=session, minimum_bytes=1
        )
    assert not destination.exists()


def test_download_validates_pdf_and_returns_hash(tmp_path):
    session = Mock()
    session.get.return_value = _response([b"%PDF-1.7\n" + b"x" * 100])
    destination = tmp_path / "paper.pdf.part"
    digest, size = download_validated_pdf(
        "https://example/paper", destination, session=session, minimum_bytes=1
    )
    assert len(digest) == 64
    assert size == destination.stat().st_size
