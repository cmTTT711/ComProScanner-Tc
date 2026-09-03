from unittest.mock import Mock

from comproscanner.literature import ScopusSearch, discover_scopus, parse_scopus_entry


def test_parse_scopus_entry_normalizes_doi_and_metadata():
    record = parse_scopus_entry(
        {
            "dc:title": "A Tc paper",
            "prism:doi": "https://doi.org/10.1000/ABC.",
            "prism:coverDate": "2025-01-02",
            "openaccessFlag": "true",
        }
    )
    assert record["doi"] == "10.1000/abc"
    assert record["year"] == "2025"
    assert record["open_access"] is True


def test_discover_scopus_is_injectable_and_deduplicates():
    response = Mock(status_code=200)
    response.json.return_value = {
        "search-results": {
            "entry": [
                {"dc:title": "One", "prism:doi": "10.1/a"},
                {"dc:title": "Duplicate", "prism:doi": "10.1/a"},
            ]
        }
    }
    response.raise_for_status.return_value = None
    session = Mock()
    session.get.return_value = response
    search = ScopusSearch("TITLE-ABS-KEY(tc)", 2025, 2025, limit=2, delay_seconds=0)

    rows = discover_scopus(search, "key", session=session, sleeper=lambda _: None)

    assert len(rows) == 1
    assert rows[0]["title"] == "One"
    assert session.get.call_count == 2
