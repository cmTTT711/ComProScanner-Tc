"""Scopus metadata discovery with no full-text or LLM side effects."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import requests

from comproscanner.documents.literature.io import normalize_doi

SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"


@dataclass(frozen=True)
class ScopusSearch:
    query: str
    start_year: int
    end_year: int
    limit: int = 500
    open_access_only: bool = False
    delay_seconds: float = 1.0

    def validate(self) -> None:
        if not self.query.strip():
            raise ValueError("Scopus query cannot be empty")
        if self.start_year > self.end_year:
            raise ValueError("start_year cannot be later than end_year")
        if self.limit < 1:
            raise ValueError("limit must be positive")


def parse_scopus_entry(entry: dict[str, Any]) -> dict[str, Any]:
    def text(value: Any) -> str:
        return "" if value is None else str(value).strip()

    cover_date = text(entry.get("prism:coverDate"))
    authors = entry.get("author") or []
    if isinstance(authors, dict):
        authors = [authors]
    affiliations = entry.get("affiliation") or []
    if isinstance(affiliations, dict):
        affiliations = [affiliations]
    return {
        "title": text(entry.get("dc:title")),
        "doi": normalize_doi(entry.get("prism:doi")),
        "eid": text(entry.get("eid")),
        "scopus_id": text(entry.get("dc:identifier")).replace("SCOPUS_ID:", ""),
        "year": cover_date[:4],
        "cover_date": cover_date,
        "journal": text(entry.get("prism:publicationName")),
        "issn": text(entry.get("prism:issn")),
        "publisher": text(entry.get("dc:publisher")),
        "document_type": text(entry.get("subtypeDescription")),
        "authors": "; ".join(
            text(item.get("authname") or item.get("ce:indexed-name"))
            for item in authors
            if isinstance(item, dict)
        ),
        "affiliations": "; ".join(
            text(item.get("affilname"))
            for item in affiliations
            if isinstance(item, dict)
        ),
        "cited_by_count": text(entry.get("citedby-count")) or "0",
        "open_access": text(entry.get("openaccessFlag")).casefold() == "true",
        "scopus_url": text(entry.get("prism:url")),
        "discovery_source": "scopus",
        "review_status": "PENDING",
        "download_status": "NOT_STARTED",
        "oa_pdf_url": "",
    }


def discover_scopus(
    search: ScopusSearch,
    api_key: str,
    *,
    excluded_dois: set[str] | None = None,
    session=requests,
    sleeper: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Return DOI-deduplicated, year-stratified metadata records."""
    search.validate()
    if not api_key.strip():
        raise ValueError("Scopus API key cannot be empty")
    excluded = {normalize_doi(value) for value in (excluded_dois or set())}
    years = list(range(search.end_year, search.start_year - 1, -1))
    base, remainder = divmod(search.limit, len(years))
    quotas = {
        year: base + (1 if index < remainder else 0) for index, year in enumerate(years)
    }
    records: dict[str, dict[str, Any]] = {}
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    for year in years:
        accepted = 0
        start = 0
        while accepted < quotas[year]:
            count = min(25, quotas[year] - accepted)
            query = f"{search.query} AND PUBYEAR = {year}"
            if search.open_access_only:
                query += " AND OPENACCESS(1)"
            params = {
                "query": query,
                "start": start,
                "count": count,
                "view": "STANDARD",
                "sort": "-citedby-count",
            }
            for attempt in range(5):
                response = session.get(
                    SCOPUS_SEARCH_URL, headers=headers, params=params, timeout=45
                )
                if response.status_code == 429 or response.status_code >= 500:
                    sleeper(min(30, 2**attempt))
                    continue
                response.raise_for_status()
                break
            else:
                raise RuntimeError(
                    f"Scopus request failed repeatedly for year={year}, start={start}"
                )
            entries = response.json().get("search-results", {}).get("entry") or []
            if not entries:
                break
            before = len(records)
            for entry in entries:
                record = parse_scopus_entry(entry)
                if record["doi"] and record["doi"] in excluded:
                    continue
                identity = record["doi"] or record["eid"] or record["title"].casefold()
                if identity:
                    records.setdefault(identity, record)
            accepted += len(records) - before
            added = len(records) - before
            start += len(entries)
            if len(entries) < count or added == 0:
                break
            sleeper(search.delay_seconds)
    return list(records.values())
