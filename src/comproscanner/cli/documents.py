"""Documents commands for the canonical workflow."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from comproscanner.presets import get_preset
from comproscanner.documents.ingestion import build_processing_plan
from comproscanner.documents.ingestion import execute_processing_plan
from comproscanner.documents.ingestion import format_processing_plan
from comproscanner.documents.ingestion import read_doi_file
from comproscanner.documents.literature import CorpusLayout
from comproscanner.documents.literature import DownloadSource
from comproscanner.documents.literature import ScopusSearch
from comproscanner.documents.literature import atomic_csv
from comproscanner.documents.literature import atomic_json
from comproscanner.documents.literature import discover_scopus
from comproscanner.documents.literature import download_validated_pdf
from comproscanner.documents.literature import existing_pdf_hashes
from comproscanner.documents.literature import normalize_doi
from comproscanner.documents.literature import read_csv
from comproscanner.documents.literature import resolve_openalex_urls
from comproscanner.documents.literature import resolve_semantic_scholar
from comproscanner.documents.literature import safe_filename
from .common import _require_network_execution


def _discover(args: argparse.Namespace) -> int:
    _require_network_execution(args)
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing API key environment variable: {args.api_key_env}")
    excluded = set()
    for path in args.exclude_csv:
        excluded.update(normalize_doi(row.get("doi")) for row in read_csv(path))
    search = ScopusSearch(
        query=args.query,
        start_year=args.start_year,
        end_year=args.end_year,
        limit=args.limit,
        open_access_only=args.open_access_only,
        delay_seconds=args.delay,
    )
    rows = discover_scopus(search, api_key, excluded_dois=excluded)
    rows.sort(
        key=lambda row: (
            -int(row.get("cited_by_count") or 0),
            -int(row.get("year") or 0),
            row.get("title", "").casefold(),
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["candidate_rank"] = rank
    output = Path(args.output).resolve()
    atomic_csv(output / "candidates.csv", rows)
    atomic_json(output / "candidates.json", rows)
    atomic_csv(output / "shortlist.csv", rows[: args.shortlist])
    atomic_json(
        output / "summary.json",
        {
            "source": "scopus",
            "query": args.query,
            "year_range": [args.start_year, args.end_year],
            "candidate_count": len(rows),
            "shortlist_count": min(len(rows), args.shortlist),
            "full_text_downloaded": False,
            "llm_called": False,
        },
    )
    print(output)
    return 0


def _acquire_oa(args: argparse.Namespace) -> int:
    _require_network_execution(args)
    rows = read_csv(args.shortlist)
    layout = CorpusLayout.from_root(args.corpus_root)
    layout.initialize()
    s2_directory = layout.downloaded_from(DownloadSource.SEMANTIC_SCHOLAR)
    openalex_directory = layout.downloaded_from(DownloadSource.OPENALEX)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    s2 = resolve_semantic_scholar(
        [row.get("doi", "") for row in rows],
        api_key=os.getenv(args.semantic_scholar_api_key_env),
    )
    known_hashes = existing_pdf_hashes(s2_directory) | existing_pdf_hashes(
        openalex_directory
    )
    manifest = []
    for index, row in enumerate(rows, start=1):
        doi = normalize_doi(row.get("doi"))
        paper = s2.get(doi) or {}
        oa = paper.get("openAccessPdf") or {}
        s2_url = str(oa.get("url") or "").strip() if isinstance(oa, dict) else ""
        candidates = [("semantic_scholar", s2_url)] if s2_url else []
        if not candidates:
            candidates.extend(("openalex", url) for url in resolve_openalex_urls(doi))
        record = {
            "candidate_rank": row.get("candidate_rank") or index,
            "doi": doi,
            "title": row.get("title", ""),
            "status": "NO_AUTHORIZED_OA_PDF",
            "provider": "",
            "url": "",
            "path": "",
            "sha256": "",
            "bytes": 0,
            "error": "",
        }
        errors = []
        for provider, url in candidates:
            if not url:
                continue
            directory = (
                s2_directory if provider == "semantic_scholar" else openalex_directory
            )
            temporary = output / f"candidate_{index:04d}.pdf.part"
            try:
                digest, size = download_validated_pdf(url, temporary)
                if digest in known_hashes:
                    temporary.unlink(missing_ok=True)
                    record.update(
                        {
                            "status": "DUPLICATE_PDF",
                            "provider": provider,
                            "url": url,
                            "sha256": digest,
                            "bytes": size,
                        }
                    )
                    break
                filename = f"{index:04d}-{safe_filename(row.get('title', ''))}.pdf"
                destination = directory / filename
                suffix = 2
                while destination.exists():
                    destination = (
                        directory
                        / f"{index:04d}-{safe_filename(row.get('title', ''))}-{suffix}.pdf"
                    )
                    suffix += 1
                temporary.replace(destination)
                known_hashes.add(digest)
                record.update(
                    {
                        "status": "DOWNLOADED",
                        "provider": provider,
                        "url": url,
                        "path": str(destination),
                        "sha256": digest,
                        "bytes": size,
                    }
                )
                break
            except Exception as exc:
                errors.append(f"{provider}: {type(exc).__name__}: {exc}")
        if errors and record["status"] == "NO_AUTHORIZED_OA_PDF":
            record["status"] = "DOWNLOAD_FAILED"
            record["error"] = " | ".join(errors[:3])
        manifest.append(record)
        atomic_json(output / "download_manifest.json", manifest)
    atomic_csv(output / "download_manifest.csv", manifest)
    counts = {}
    for record in manifest:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    atomic_json(
        output / "summary.json",
        {"status_counts": counts, "llm_called": False, "paywall_bypassed": False},
    )
    print(output)
    return 1 if counts.get("DOWNLOAD_FAILED") else 0


def _process_articles(args: argparse.Namespace) -> int:
    preset = get_preset(args.preset)
    dois = read_doi_file(args.doi_file)
    plan = build_processing_plan(
        preset=args.preset,
        sources=args.source,
        folder_path=args.folder,
        dois=dois,
        execute_network=args.execute_network,
    )
    print(format_processing_plan(plan))
    if not args.execute_processing:
        return 0
    if plan.network_required and not args.execute_network:
        raise SystemExit(
            "Selected sources require network access. Re-run with both "
            "--execute-processing and --execute-network only after explicit approval."
        )
    workspace = Path(
        getattr(args, "workspace", None) or f"data/literature/processing/{preset.name}"
    ).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    previous = Path.cwd()
    try:
        os.chdir(workspace)
        execute_processing_plan(
            plan,
            property_keywords=preset.property_keywords,
            main_property_keyword=preset.main_property_keyword,
            processing_kwargs=preset.processing_kwargs,
            dois=dois,
            save_xml=args.save_xml,
            save_pdf=args.save_pdf,
        )
    finally:
        os.chdir(previous)
    print(workspace)
    return 0
