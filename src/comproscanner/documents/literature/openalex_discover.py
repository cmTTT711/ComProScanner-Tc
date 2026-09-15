"""OpenAlex metadata discovery with no full-text or LLM side effects."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import requests

from comproscanner.documents.literature.io import normalize_doi

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


@dataclass(frozen=True)
class OpenalexSearch:
    query: str
    start_year: int
    end_year: int
    document_types: tuple[str, ...] = ("article", "review")
    per_page: int = 200
    max_records: int = 5000
    delay_seconds: float = 0.5
    mailto: str = ""
    api_key: str = ""

    def validate(self) -> None:
        if not self.query.strip():
            raise ValueError("OpenAlex query cannot be empty")
        if self.start_year > self.end_year:
            raise ValueError("start_year cannot be later than end_year")
        if not 1 <= self.per_page <= 200:
            raise ValueError("per_page must be within 1..200")
        if self.max_records < 1:
            raise ValueError("max_records must be positive")
        if not self.document_types:
            raise ValueError("document_types cannot be empty")


def parse_openalex_work(work: dict[str, Any]) -> dict[str, Any]:
    def text(value: Any) -> str:
        return "" if value is None else str(value).strip()

    source = (work.get("primary_location") or {}).get("source") or {}
    open_access = work.get("open_access") or {}
    best_oa = work.get("best_oa_location") or {}
    has_content = work.get("has_content") or {}
    content_urls = work.get("content_urls") or {}
    authorships = work.get("authorships") or []
    affiliations: list[str] = []
    for authorship in authorships:
        for institution in authorship.get("institutions") or []:
            name = text(institution.get("display_name"))
            if name and name not in affiliations:
                affiliations.append(name)
    issns = source.get("issn") or []
    return {
        "title": text(work.get("title") or work.get("display_name")),
        "doi": normalize_doi(work.get("doi")),
        "openalex_id": text(work.get("id")).rsplit("/", 1)[-1],
        "year": str(work.get("publication_year") or ""),
        "publication_date": text(work.get("publication_date")),
        "journal": text(source.get("display_name")),
        "issn": text(issns[0] if issns else ""),
        "publisher": text(source.get("host_organization_name")),
        "document_type": text(work.get("type")),
        "authors": "; ".join(
            text((item.get("author") or {}).get("display_name"))
            for item in authorships
        ),
        "affiliations": "; ".join(affiliations),
        "cited_by_count": str(work.get("cited_by_count") or 0),
        "open_access": bool(open_access.get("is_oa")),
        "oa_status": text(open_access.get("oa_status")),
        "oa_url": text(open_access.get("oa_url")),
        "oa_pdf_url": text(best_oa.get("pdf_url")),
        "has_content_pdf": bool(has_content.get("pdf")),
        "content_pdf_url": text(content_urls.get("pdf")),
        "is_retracted": bool(work.get("is_retracted")),
        "openalex_url": text(work.get("id")),
        "discovery_source": "openalex",
        "review_status": "PENDING",
        "download_status": "NOT_STARTED",
    }


def discover_openalex(
    search: OpenalexSearch,
    *,
    session=requests,
    sleeper: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Return DOI-deduplicated metadata records via cursor pagination."""
    search.validate()
    filters = [
        f"title_and_abstract.search:{search.query}",
        f"publication_year:{search.start_year}-{search.end_year}",
        "type:" + "|".join(search.document_types),
    ]
    params: dict[str, Any] = {
        "filter": ",".join(filters),
        "per-page": min(search.per_page, search.max_records),
        "cursor": "*",
    }
    if search.mailto:
        params["mailto"] = search.mailto
    if search.api_key:
        headers = {"Authorization": f"Bearer {search.api_key}"}
    else:
        headers = {}
    records: dict[str, dict[str, Any]] = {}
    while True:
        for attempt in range(5):
            response = session.get(
                OPENALEX_WORKS_URL, params=dict(params), headers=headers, timeout=45
            )
            if response.status_code == 429 or response.status_code >= 500:
                sleeper(min(30, 2**attempt))
                continue
            if not response.ok:
                raise RuntimeError(f"OpenAlex metadata HTTP {response.status_code}")
            break
        else:
            raise RuntimeError("OpenAlex request failed repeatedly")
        payload = response.json()
        works = payload.get("results") or []
        for work in works:
            record = parse_openalex_work(work)
            identity = (
                record["doi"] or record["openalex_id"] or record["title"].casefold()
            )
            if identity:
                records.setdefault(identity, record)
            if len(records) >= search.max_records:
                break
        cursor = (payload.get("meta") or {}).get("next_cursor")
        if not works or not cursor or len(records) >= search.max_records:
            break
        params["cursor"] = cursor
        params["per-page"] = min(search.per_page, search.max_records - len(records))
        sleeper(search.delay_seconds)
    return list(records.values())
