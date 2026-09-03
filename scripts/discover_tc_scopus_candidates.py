"""Discover Tc-related research articles from Scopus without downloading full text.

The script intentionally performs metadata discovery only. It never invokes an
LLM and never downloads article XML/PDF files. API credentials are read only
from ``SCOPUS_API_KEY`` and are not written to the output files.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from comproscanner.literature import (
    atomic_json as _atomic_json,
    normalize_doi as _normalize_doi,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "literature_discovery" / "tc_scopus_2020_2026"
SCOPUS_URL = "https://api.elsevier.com/content/search/scopus"
QUERY_BASE = (
    'TITLE-ABS-KEY(("Curie temperature" OR "Curie point" OR '
    '"ferroelectric transition" OR "magnetic transition") AND '
    '(material* OR ceramic* OR ferroelectric* OR multiferroic* OR magnet*)) '
    'AND DOCTYPE(ar) AND LANGUAGE(english)'
)

HIGH_VALUE_TERMS = {
    "curie temperature": 12,
    "curie point": 12,
    "ferroelectric transition": 9,
    "magnetic transition": 7,
    "multiferroic": 8,
    "ferroelectric": 6,
    "perovskite": 5,
    "bifeo3": 6,
    "batio3": 6,
    "ceramic": 4,
    "magnetocaloric": 3,
    "dielectric": 2,
}


def atomic_json(path: Path, data: object) -> None:
    _atomic_json(path, data)


def text(value) -> str:
    return "" if value is None else str(value).strip()


def normalize_doi(value: str) -> str:
    return _normalize_doi(value)


def score_candidate(item: dict) -> int:
    title = item["title"].casefold()
    score = sum(weight for term, weight in HIGH_VALUE_TERMS.items() if term in title)
    if item["open_access"]:
        score += 3
    try:
        year = int(item["year"])
        score += max(0, year - 2014) // 3
    except (TypeError, ValueError):
        pass
    try:
        score += min(8, int(item["cited_by_count"]) // 20)
    except (TypeError, ValueError):
        pass
    if not item["doi"]:
        score -= 8
    return score


def parse_entry(entry: dict) -> dict:
    cover_date = text(entry.get("prism:coverDate"))
    authors = entry.get("author") or []
    if isinstance(authors, dict):
        authors = [authors]
    author_names = [
        text(author.get("authname") or author.get("ce:indexed-name"))
        for author in authors
        if isinstance(author, dict)
    ]
    affiliations = entry.get("affiliation") or []
    if isinstance(affiliations, dict):
        affiliations = [affiliations]
    affiliation_names = [
        text(aff.get("affilname")) for aff in affiliations if isinstance(aff, dict)
    ]
    open_access = text(entry.get("openaccessFlag")).casefold() == "true"
    record = {
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
        "authors": "; ".join(filter(None, author_names)),
        "affiliations": "; ".join(filter(None, affiliation_names)),
        "cited_by_count": text(entry.get("citedby-count")) or "0",
        "open_access": open_access,
        "scopus_url": text(entry.get("prism:url")),
        "discovery_source": "scopus",
        "review_status": "PENDING",
        "download_status": "NOT_STARTED",
        "oa_pdf_url": "",
    }
    record["priority_score"] = score_candidate(record)
    return record


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["title", "doi"]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def fetch_candidates(
    api_key: str,
    limit: int,
    delay: float,
    start_year: int,
    end_year: int,
    open_access_only: bool = False,
    excluded_dois: set[str] | None = None,
) -> list[dict]:
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    records: dict[str, dict] = {}
    excluded_dois = excluded_dois or set()
    page_size = 25
    years = list(range(end_year, start_year - 1, -1))
    base_quota, remainder = divmod(limit, len(years))
    quotas = {
        year: base_quota + (1 if index < remainder else 0)
        for index, year in enumerate(years)
    }
    for year in years:
        year_count = 0
        start = 0
        while year_count < quotas[year]:
            params = {
                "query": (
                    f"{QUERY_BASE} AND PUBYEAR = {year}"
                    + (" AND OPENACCESS(1)" if open_access_only else "")
                ),
                "start": start,
                "count": min(page_size, quotas[year] - year_count),
                "view": "STANDARD",
                "sort": "-citedby-count",
            }
            for attempt in range(5):
                response = requests.get(SCOPUS_URL, headers=headers, params=params, timeout=45)
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    time.sleep(min(30, 2 ** attempt))
                    continue
                response.raise_for_status()
                break
            else:
                raise RuntimeError(
                    f"Scopus request failed repeatedly for year={year}, start={start}"
                )

            payload = response.json().get("search-results", {})
            entries = payload.get("entry") or []
            if not entries:
                break
            before = len(records)
            for entry in entries:
                record = parse_entry(entry)
                key = record["doi"] or record["eid"] or record["title"].casefold()
                if record["doi"] in excluded_dois:
                    continue
                if key:
                    records.setdefault(key, record)
            added = len(records) - before
            year_count += added
            start += len(entries)
            print(
                f"Year {year}: {year_count}/{quotas[year]}; total {len(records)}/{limit}",
                flush=True,
            )
            if len(entries) < params["count"]:
                break
            time.sleep(delay)
    return list(records.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--shortlist", type=int, default=200)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--open-access-only", action="store_true")
    parser.add_argument(
        "--exclude-csv",
        type=Path,
        action="append",
        default=[],
        help="CSV files whose DOI column should be excluded (repeatable).",
    )
    args = parser.parse_args()
    if args.limit < 1 or args.shortlist < 1 or args.shortlist > args.limit:
        raise ValueError("Require 1 <= shortlist <= limit")
    if args.start_year > args.end_year:
        raise ValueError("start-year must not be later than end-year")

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("SCOPUS_API_KEY")
    if not api_key:
        raise RuntimeError("SCOPUS_API_KEY is not configured")

    excluded_dois: set[str] = set()
    for csv_path in args.exclude_csv:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
            for item in csv.DictReader(stream):
                doi = normalize_doi(item.get("doi", ""))
                if doi:
                    excluded_dois.add(doi)
    rows = fetch_candidates(
        api_key,
        args.limit,
        args.delay,
        args.start_year,
        args.end_year,
        open_access_only=args.open_access_only,
        excluded_dois=excluded_dois,
    )
    rows.sort(
        key=lambda row: (
            -int(row["priority_score"]),
            -int(row["year"] or 0),
            -int(row["cited_by_count"] or 0),
            row["title"].casefold(),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["candidate_rank"] = index
    shortlist = rows[: args.shortlist]

    output_dir = args.output_dir.resolve()
    write_csv(output_dir / "scopus_candidates_500.csv", rows)
    atomic_json(output_dir / "scopus_candidates_500.json", rows)
    write_csv(output_dir / "review_shortlist_200.csv", shortlist)
    atomic_json(output_dir / "review_shortlist_200.json", shortlist)
    atomic_json(
        output_dir / "run_summary.json",
        {
            "task": "TC_LITERATURE_DISCOVERY_SCOPUS_01",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "query": QUERY_BASE,
            "sampling": "year-stratified; approximately equal quota per year",
            "open_access_only": args.open_access_only,
            "excluded_doi_count": len(excluded_dois),
            "requested_candidates": args.limit,
            "retrieved_candidates": len(rows),
            "shortlist_size": len(shortlist),
            "year_range": [args.start_year, args.end_year],
            "document_type": "Article",
            "language": "English",
            "llm_called": False,
            "full_text_downloaded": False,
        },
    )
    print(f"Saved {len(rows)} candidates and {len(shortlist)} shortlisted records to {output_dir}")


if __name__ == "__main__":
    main()
