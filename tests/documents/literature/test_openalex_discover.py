from unittest.mock import Mock

import pytest

from comproscanner.documents.literature import (
    OpenalexSearch,
    discover_openalex,
    parse_openalex_work,
)


def _work(**overrides):
    work = {
        "id": "https://openalex.org/W3111189013",
        "title": "A multiferroic paper",
        "doi": "https://doi.org/10.1103/PhysRevLett.125.247601",
        "type": "article",
        "publication_year": 2020,
        "publication_date": "2020-12-11",
        "cited_by_count": 278,
        "primary_location": {
            "source": {
                "display_name": "Physical Review Letters",
                "issn": ["0031-9007", "1079-7114"],
                "host_organization_name": "American Physical Society",
            }
        },
        "authorships": [
            {
                "author": {"display_name": "Alice Smith"},
                "institutions": [{"display_name": "ETH Zurich"}],
            },
            {
                "author": {"display_name": "Bob Jones"},
                "institutions": [
                    {"display_name": "ETH Zurich"},
                    {"display_name": "PSI"},
                ],
            },
        ],
        "open_access": {"is_oa": False, "oa_status": "closed"},
        "best_oa_location": None,
        "has_content": {"pdf": False, "grobid_xml": False},
        "content_urls": None,
        "is_retracted": False,
    }
    work.update(overrides)
    return work


def test_parse_openalex_work_normalizes_doi_and_metadata():
    record = parse_openalex_work(_work())
    assert record["doi"] == "10.1103/physrevlett.125.247601"
    assert record["openalex_id"] == "W3111189013"
    assert record["year"] == "2020"
    assert record["journal"] == "Physical Review Letters"
    assert record["issn"] == "0031-9007"
    assert record["publisher"] == "American Physical Society"
    assert record["authors"] == "Alice Smith; Bob Jones"
    assert record["affiliations"] == "ETH Zurich; PSI"
    assert record["open_access"] is False
    assert record["oa_status"] == "closed"
    assert record["oa_url"] == ""
    assert record["has_content_pdf"] is False
    assert record["content_pdf_url"] == ""
    assert record["discovery_source"] == "openalex"
    assert record["download_status"] == "NOT_STARTED"


def test_parse_openalex_work_extracts_oa_and_archive_content():
    record = parse_openalex_work(
        _work(
            open_access={
                "is_oa": True,
                "oa_status": "green",
                "oa_url": "https://repository.example.org/1234",
            },
            best_oa_location={"pdf_url": "https://example.org/preprint.pdf"},
            has_content={"pdf": True, "grobid_xml": True},
            content_urls={
                "pdf": "https://content.openalex.org/works/W3111189013.pdf"
            },
        )
    )
    assert record["open_access"] is True
    assert record["oa_status"] == "green"
    assert record["oa_url"] == "https://repository.example.org/1234"
    assert record["oa_pdf_url"] == "https://example.org/preprint.pdf"
    assert record["has_content_pdf"] is True
    assert (
        record["content_pdf_url"]
        == "https://content.openalex.org/works/W3111189013.pdf"
    )


def _page(results, next_cursor=None):
    response = Mock(status_code=200)
    response.raise_for_status.return_value = None
    meta = {"next_cursor": next_cursor} if next_cursor else {}
    response.json.return_value = {"meta": meta, "results": results}
    return response


def test_discover_openalex_paginates_with_cursor_and_deduplicates():
    duplicate = _work()
    other = _work(
        id="https://openalex.org/W9999999999",
        title="Another paper",
        doi="https://doi.org/10.1000/other",
        cited_by_count=5,
    )
    session = Mock()
    session.get.side_effect = [
        _page([duplicate, other], next_cursor="CURSOR-2"),
        _page([duplicate]),
    ]
    search = OpenalexSearch(
        "multiferroic magnetoelectric", 2020, 2026, delay_seconds=0
    )

    rows = discover_openalex(search, session=session, sleeper=lambda _: None)

    assert len(rows) == 2
    assert session.get.call_count == 2
    second_params = session.get.call_args_list[1].kwargs["params"]
    assert second_params["cursor"] == "CURSOR-2"


def test_discover_openalex_stops_at_max_records():
    session = Mock()
    session.get.side_effect = [
        _page([_work(), _work(id="https://openalex.org/W2", doi="10.1/other")], next_cursor="CURSOR-2")
    ]
    search = OpenalexSearch("tc", 2020, 2020, max_records=1, delay_seconds=0)

    rows = discover_openalex(search, session=session, sleeper=lambda _: None)

    assert len(rows) == 1
    assert session.get.call_count == 1


def test_discover_openalex_requires_filter_params():
    session = Mock()
    session.get.side_effect = [_page([_work()])]
    search = OpenalexSearch("multiferroic magnetoelectric", 2020, 2026, delay_seconds=0)

    discover_openalex(search, session=session, sleeper=lambda _: None)

    params = session.get.call_args.kwargs["params"]
    assert "title_and_abstract.search:multiferroic magnetoelectric" in params["filter"]
    assert "publication_year:2020-2026" in params["filter"]
    assert "type:article|review" in params["filter"]
    assert params["cursor"] == "*"
    assert "api_key" not in params
    assert "mailto" not in params


def test_discover_openalex_forwards_api_key_and_mailto():
    session = Mock()
    session.get.side_effect = [_page([_work()])]
    search = OpenalexSearch(
        "tc",
        2020,
        2026,
        delay_seconds=0,
        mailto="user@example.org",
        api_key="secret-key",
    )

    discover_openalex(search, session=session, sleeper=lambda _: None)

    params = session.get.call_args.kwargs["params"]
    assert "api_key" not in params
    assert session.get.call_args.kwargs["headers"]["Authorization"] == "Bearer secret-key"
    assert params["mailto"] == "user@example.org"


def test_openalex_search_validation_rejects_invalid_ranges():
    with pytest.raises(ValueError):
        OpenalexSearch("query", 2026, 2020).validate()
    with pytest.raises(ValueError):
        OpenalexSearch("  ", 2020, 2026).validate()
    with pytest.raises(ValueError):
        OpenalexSearch("query", 2020, 2026, per_page=201).validate()
    with pytest.raises(ValueError):
        OpenalexSearch("query", 2020, 2026, document_types=()).validate()
