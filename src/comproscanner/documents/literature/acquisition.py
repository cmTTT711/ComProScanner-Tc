"""DOI manifest -> public PDFs -> OpenAlex archive -> external browser handoff.

No models or browser dependencies are imported here. A run is resumable; network
attempts and archive budget are checkpointed before each request.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import requests

from .io import atomic_csv, atomic_json, normalize_doi
from .oa import download_validated_pdf, hash_file
from .openalex_discover import parse_openalex_work


def publisher_profile(publisher: str) -> str:
    """Map metadata publisher names to installed InstSci profiles, not DOI guesses."""
    name = publisher.casefold()
    for profile, aliases in {
        "elsevier": ("elsevier",), "springer": ("springer", "nature portfolio"),
        "aps": ("american physical society",),
        "aip": ("american institute of physics", "aip publishing"),
        "acs": ("american chemical society",), "wiley": ("wiley",),
        "iop": ("iop publishing", "institute of physics"),
        "annual-reviews": ("annual reviews",), "ieee": ("ieee", "electrical and electronics"),
        "rsc": ("royal society of chemistry",),
    }.items():
        if any(alias in name for alias in aliases):
            return profile
    return "unknown"


def merge_candidates(*sources: list[dict], limit: int | None = None) -> list[dict]:
    """Round-robin source lists, merge metadata by DOI; retain source provenance."""
    merged: dict[str, dict] = {}
    for index in range(max((len(rows) for rows in sources), default=0)):
        for rows in sources:
            if index >= len(rows):
                continue
            row = rows[index]
            doi = normalize_doi(row.get("doi"))
            if not doi.startswith("10.") or "/" not in doi:
                continue
            target = merged.setdefault(doi, {"doi": doi, "discovery_sources": []})
            provenance = row.get("discovery_sources") or [row.get("discovery_source", "unknown")]
            if isinstance(provenance, str):
                provenance = [provenance]
            for source in provenance:
                if source not in target["discovery_sources"]:
                    target["discovery_sources"].append(source)
            for key, value in row.items():
                if key not in ("doi", "discovery_sources") and value not in (None, ""):
                    if key not in target or target[key] in (None, ""):
                        target[key] = value
    return list(merged.values())[:limit]


def verify_pdf(path: Path, row: dict) -> dict:
    """Verify identity on the first two pages, avoiding reference-list DOI hits."""
    import pymupdf

    with pymupdf.open(path) as document:
        if not len(document) or document.needs_pass:
            raise ValueError("empty or encrypted PDF")
        text = " ".join(document[i].get_text() for i in range(min(2, len(document))))
        compact = re.sub(r"\s+", "", text).casefold()
        title_words = re.findall(r"[a-z0-9]+", str(row.get("title", "")).casefold())
        text_words = set(re.findall(r"[a-z0-9]+", text.casefold()))
        overlap = sum(word in text_words for word in title_words) / max(1, len(title_words))
        supplement_pattern = r"supporting information|supplementary (?:information|material|data)"
        # ACS full articles include a 'Supporting Information' navigation label
        # above ABSTRACT. Treat a heading as a supplement, not that toolbar link.
        supplementary = bool(re.search(supplement_pattern, text[:150], re.I) or (
            re.search(supplement_pattern, text[:500], re.I)
            and not re.search(r"\babstract\b", text[:1500], re.I)
        ) or re.search(r"in the format provided by the\s+authors and unedited", text[:1000], re.I))
        doi = normalize_doi(row.get("doi"))
        matched = not supplementary and (
            bool(doi and doi in compact) or (len(title_words) >= 6 and overlap >= .9)
        )
        return {"verified": matched, "pages": len(document),
                "title_overlap": round(overlap, 3), "supplementary": supplementary,
                "sha256": hash_file(path), "bytes": path.stat().st_size}


def _safe_error(exc: Exception) -> str:
    # HTTP exception strings can contain signed URLs or API credentials.
    response = getattr(exc, "response", None)
    return f"HTTP {response.status_code}" if response is not None else type(exc).__name__


def _public_locations(work: dict) -> list[str]:
    locations = [work.get("best_oa_location")] + list(work.get("locations") or [])
    return list(dict.fromkeys(
        loc["pdf_url"] for loc in locations
        if isinstance(loc, dict) and loc.get("is_oa") and loc.get("pdf_url")
        and urlsplit(loc["pdf_url"]).scheme in ("http", "https")
    ))


def _fill_publisher(record: dict, session) -> None:
    needs_canonical = publisher_profile(record.get("publisher") or "") == "aps" and not record.get("canonical_doi_checked")
    if (record.get("publisher") or record.get("publisher_checked")) and not needs_canonical:
        return
    try:
        response = session.get("https://api.crossref.org/works/" + quote(record["doi"], safe=""), timeout=30)
        response.raise_for_status()
        message = response.json().get("message", {})
        record["publisher"] = message.get("publisher") or record.get("publisher", "")
        # DOI identity is case-insensitive; publisher URL paths need not be.
        canonical = message.get("DOI", "")
        resource = (message.get("resource") or {}).get("primary") or {}
        links = [resource.get("URL", "")] + [link.get("URL", "") for link in message.get("link", [])]
        for link in links:
            path = unquote(urlsplit(link).path)
            start = path.find("10.")
            if start >= 0 and normalize_doi(path[start:]) == record["doi"]:
                canonical = path[start:]
                break
        if canonical and normalize_doi(canonical) == record["doi"]:
            record["download_doi"] = canonical
        record["canonical_doi_checked"] = True
        record["publisher_checked"] = True
        record.pop("publisher_error", None)
    except Exception as exc:
        record["publisher_error"] = _safe_error(exc)


def acquire_pdfs(rows: list[dict], output: str | Path, *, api_key: str,
                 max_archive_requests: int = 50, session=requests,
                 browser_manifest: str | Path | None = None) -> dict:
    """Run bounded downloads, or import browser results into the same manifest.

    Existing attempts are not retried automatically. Missing PDFs are handed to
    InstSci through remaining_dois.txt. A new run directory explicitly retries.
    """
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    rows = merge_candidates(rows)
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        records = json.loads(manifest_path.read_text(encoding="utf-8"))
        if [r["doi"] for r in records] != [r["doi"] for r in rows]:
            raise ValueError("Run DOI list changed; use a new output directory")
    else:
        records = [{**row, "status": "pending", "path": "", "provider": "",
                    "attempts": [], "metadata_checked": False} for row in rows]

    def save() -> None:
        atomic_json(manifest_path, records)

    # Recover interrupted reservations conservatively: no silent billable retry.
    archive_used = sum(a["stage"] == "openalex_archive"
                       for r in records for a in r["attempts"])
    browser_rows = []
    if browser_manifest:
        payload = json.loads(Path(browser_manifest).read_text(encoding="utf-8"))
        browser_rows = payload if isinstance(payload, list) else payload.get("results", [])
    browser_by_doi = {normalize_doi(r.get("doi")): r for r in browser_rows}
    for number, record in enumerate(records, 1):
        doi = record["doi"]
        destination = root / "pdfs" / (hashlib.sha256(doi.encode()).hexdigest()[:20] + ".pdf")
        quarantined = root / "quarantine" / destination.name
        if not destination.exists() and quarantined.exists():
            try:
                check = verify_pdf(quarantined, record)
                if check["verified"]:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    quarantined.replace(destination)
                    previous = next((a for a in reversed(record["attempts"])
                                     if a["status"] == "unverified"), {})
                    record["provider"] = previous.get("stage", "local_recheck")
                    previous["status"] = "downloaded"
            except Exception:
                pass
        if destination.exists():
            try:
                check = verify_pdf(destination, record)
                if check["verified"]:
                    record.update(check, status="downloaded", path=str(destination))
                    if not browser_manifest:
                        _fill_publisher(record, session)
                    save()
                    continue
                quarantined.parent.mkdir(parents=True, exist_ok=True)
                destination.replace(quarantined)
                record.update(check, status="unverified", path="", quarantine_path=str(quarantined))
            except Exception:
                pass
        if record["status"] == "downloaded":
            record.update(status="needs_browser", path="", verified=False)
        if browser_manifest:
            found = browser_by_doi.get(doi, {})
            pdf = found.get("pdf_path") or found.get("path")
            if pdf and Path(pdf).is_file():
                try:
                    check = verify_pdf(Path(pdf), record)
                    if check["verified"]:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(pdf, destination)
                        record.update(check, status="downloaded", provider="instsci",
                                      path=str(destination))
                        record.pop("browser_error", None)
                        record["source_url"] = str(found.get("pdf_url") or "").split("?", 1)[0]
                    else:
                        record["status"] = "unverified"
                        record["browser_error"] = "PDF_IDENTITY_MISMATCH"
                        record["quarantine_path"] = str(Path(pdf).resolve())
                except Exception as exc:
                    record["browser_error"] = _safe_error(exc)
            elif found:
                record["browser_error"] = found.get("reason") or found.get("status")
            save()
            continue
        if not record["metadata_checked"]:
            try:
                response = session.get(
                    "https://api.openalex.org/works/https://doi.org/" + quote(doi, safe=""),
                    headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                    timeout=30,
                )
                response.raise_for_status()
                work = response.json()
                meta = parse_openalex_work(work)
                for key in ("publisher", "journal", "openalex_id", "oa_status",
                            "open_access", "has_content_pdf", "content_pdf_url"):
                    if meta.get(key) not in (None, ""):
                        record[key] = meta[key]
                record["public_pdf_urls"] = _public_locations(work)
                record["best_oa_version"] = (work.get("best_oa_location") or {}).get("version", "")
                record["metadata_checked"] = True
                record.pop("metadata_error", None)
            except Exception as exc:
                record["metadata_error"] = _safe_error(exc)
            save()
        _fill_publisher(record, session)
        save()
        urls = record.get("public_pdf_urls", [])[:3]
        candidates = [("direct_oa", url) for url in urls]
        archive_url = record.get("content_pdf_url")
        if archive_url and api_key and urlsplit(archive_url).hostname == "content.openalex.org":
            candidates.append(("openalex_archive", archive_url))
        for stage, url in candidates:
            identifier = hashlib.sha256(url.encode()).hexdigest()
            if any(a.get("url_hash") == identifier for a in record["attempts"]):
                continue
            if stage == "openalex_archive":
                if archive_used >= max_archive_requests:
                    record["archive_budget_exhausted"] = True
                    continue
                archive_used += 1
            attempt = {"stage": stage, "url_hash": identifier, "status": "started"}
            record["attempts"].append(attempt)
            save()
            temp = root / "quarantine" / (destination.stem + ".part")
            try:
                kwargs = {}
                if stage == "openalex_archive":
                    kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}
                download_validated_pdf(url, temp, session=session, **kwargs)
                check = verify_pdf(temp, record)
                attempt.update(status="downloaded" if check["verified"] else "unverified")
                if check["verified"]:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    temp.replace(destination)
                    record.update(check, status="downloaded", provider=stage, path=str(destination))
                    record["source_url"] = url.split("?", 1)[0]
                    save()
                    break
                temp.replace(temp.with_suffix(".pdf"))
                record["status"] = "unverified"
            except Exception as exc:
                attempt.update(status="failed", error=_safe_error(exc))
            save()
        if record["status"] != "downloaded":
            record["status"] = "needs_browser" if record["status"] != "unverified" else "unverified"
        save()
        print(f"[{number}/{len(records)}] {doi}: {record['status']}", flush=True)
    remaining = [r for r in records if r["status"] != "downloaded"]
    (root / "remaining_dois.txt").write_text("".join(r["doi"] + "\n" for r in remaining), encoding="utf-8")
    atomic_json(root / "remaining.json", remaining)
    groups: dict[str, list[str]] = {}
    for row in remaining:
        groups.setdefault(publisher_profile(row.get("publisher") or ""), []).append(row.get("download_doi") or row["doi"])
    handoff = root / "browser_input"
    handoff.mkdir(exist_ok=True)
    # Empty old groups on resume so a stale DOI file cannot trigger re-downloads.
    for profile in set(groups) | {p.stem for p in handoff.glob("*.txt")}:
        (handoff / f"{profile}.txt").write_text("".join(d + "\n" for d in groups.get(profile, [])), encoding="utf-8")
    atomic_csv(root / "manifest.csv", [{k: r.get(k, "") for k in (
        "doi", "title", "publisher", "journal", "oa_status", "status", "provider", "path",
        "pages", "bytes", "sha256", "source_url", "browser_error", "metadata_error")} for r in records])
    summary = {"selected": len(records), "status_counts": dict(Counter(r["status"] for r in records)),
               "download_sources": dict(Counter(r["provider"] for r in records if r["status"] == "downloaded")),
               "archive_requests_reserved": archive_used,
               "archive_cost_upper_bound_usd": round(archive_used * .01, 2),
               "publisher_counts": dict(Counter(r.get("publisher") or "Unknown" for r in records)),
               "browser_groups": {k: len(v) for k, v in groups.items()},
               "llm_called": False}
    atomic_json(root / "summary.json", summary)
    return summary
