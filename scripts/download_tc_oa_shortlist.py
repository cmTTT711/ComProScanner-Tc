"""Download legally available OA PDFs for the reviewed Scopus shortlist.

Semantic Scholar is used only to resolve open-access PDF locations. Downloads
are validated by PDF signature and SHA-256 and are never allowed to overwrite
an existing numbered corpus file.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHORTLIST = (
    ROOT
    / "outputs"
    / "literature_discovery"
    / "tc_scopus_2020_2026"
    / "review_shortlist_200.csv"
)
DEFAULT_OUTPUT = (
    ROOT / "outputs" / "literature_discovery" / "tc_scopus_2020_2026" / "oa_downloads"
)
PDF_DIR = ROOT / "pdfs"
S2_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
USER_AGENT = "ComProScanner academic OA downloader/1.0"


def safe_name(title: str, limit: int = 105) -> str:
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", title)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value[:limit].rstrip(" .") or "untitled")


def normalize_doi(value: str) -> str:
    value = (value or "").strip().casefold()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value.rstrip(".,; ")


def atomic_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["doi", "status"]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def resolve_s2(rows: list[dict], cache_path: Path) -> dict[str, dict]:
    resolved: dict[str, dict] = (
        json.loads(cache_path.read_text(encoding="utf-8"))
        if cache_path.exists()
        else {}
    )
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    fields = "title,externalIds,openAccessPdf,isOpenAccess,year,venue"
    pending = [row for row in rows if normalize_doi(row["doi"]) not in resolved]
    for offset in range(0, len(pending), 50):
        batch = pending[offset : offset + 50]
        identifiers = [f"DOI:{normalize_doi(row['doi'])}" for row in batch]
        response = None
        for attempt in range(10):
            response = requests.post(
                S2_BATCH_URL,
                params={"fields": fields},
                headers=headers,
                json={"ids": identifiers},
                timeout=60,
            )
            if response.status_code == 429 or 500 <= response.status_code < 600:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    wait_seconds = float(retry_after)
                except ValueError:
                    wait_seconds = 2 ** attempt
                wait_seconds = min(45.0, max(2.0, wait_seconds))
                print(
                    f"Semantic Scholar throttled ({response.status_code}); "
                    f"retrying in {wait_seconds:.0f}s",
                    flush=True,
                )
                time.sleep(wait_seconds)
                continue
            response.raise_for_status()
            break
        else:
            raise RuntimeError(f"Semantic Scholar batch failed at offset {offset}")
        papers = response.json()
        for row, paper in zip(batch, papers):
            doi = normalize_doi(row["doi"])
            if isinstance(paper, dict):
                resolved[doi] = paper
            else:
                resolved[doi] = {}
        atomic_json(cache_path, resolved)
        print(
            f"Resolved OA metadata {len(resolved)}/{len(rows)}",
            flush=True,
        )
        time.sleep(3.0)
    return resolved


def existing_hashes(pdf_dir: Path) -> set[str]:
    values = set()
    for path in pdf_dir.glob("*.pdf"):
        digest = hashlib.sha256()
        try:
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            values.add(digest.hexdigest())
        except OSError:
            continue
    return values


def download_pdf(url: str, temporary: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    headers = {"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*;q=0.5"}
    with requests.get(url, headers=headers, stream=True, timeout=(30, 120), allow_redirects=True) as response:
        response.raise_for_status()
        first = b""
        with temporary.open("wb") as stream:
            for chunk in response.iter_content(1024 * 256):
                if not chunk:
                    continue
                if not first:
                    first = chunk[:8]
                stream.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        if not first.startswith(b"%PDF-"):
            temporary.unlink(missing_ok=True)
            raise ValueError("response is not a PDF")
    if size < 10_000:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"PDF is unexpectedly small ({size} bytes)")
    return digest.hexdigest(), size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shortlist", type=Path, default=DEFAULT_SHORTLIST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pdf-dir", type=Path, default=PDF_DIR)
    parser.add_argument("--start-id", type=int, default=101)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--finalize-only", action="store_true")
    args = parser.parse_args()

    with args.shortlist.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.pdf_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "download_manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else []
    )
    if args.finalize_only:
        write_csv(args.output_dir / "download_manifest.csv", manifest)
        counts: dict[str, int] = {}
        for item in manifest:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        atomic_json(
            args.output_dir / "download_summary.json",
            {
                "task": "TC_OA_DOWNLOAD_101_PLUS_01",
                "shortlist_count": len(rows),
                "manifest_records": len(manifest),
                "status_counts": counts,
                "downloaded_total": sum(
                    count for status, count in counts.items() if status.startswith("DOWNLOADED")
                ),
                "llm_called": False,
                "paywall_bypassed": False,
                "pdf_directory": str(args.pdf_dir.resolve()),
            },
        )
        print(json.dumps(counts, ensure_ascii=False), flush=True)
        return

    resolved = resolve_s2(rows, args.output_dir / "s2_oa_resolution_cache.json")
    known_hashes = existing_hashes(args.pdf_dir)
    completed_dois = {
        normalize_doi(item.get("doi", ""))
        for item in manifest
        if item.get("status") == "DOWNLOADED"
    }
    used_ids = {
        int(item["paper_id"])
        for item in manifest
        if item.get("paper_id") is not None
    }
    next_id = max(used_ids, default=args.start_id - 1) + 1

    existing_manifest_dois = {normalize_doi(item.get("doi", "")) for item in manifest}
    for index, row in enumerate(rows, start=1):
        doi = normalize_doi(row["doi"])
        if doi in completed_dois or doi in existing_manifest_dois:
            continue
        paper = resolved.get(doi) or {}
        oa = paper.get("openAccessPdf") or {}
        url = (oa.get("url") or "").strip() if isinstance(oa, dict) else ""
        record = {
            "candidate_rank": int(row.get("candidate_rank") or index),
            "paper_id": None,
            "title": row.get("title", ""),
            "doi": doi,
            "year": row.get("year", ""),
            "journal": row.get("journal", ""),
            "s2_is_open_access": bool(paper.get("isOpenAccess")),
            "oa_pdf_url": url,
            "status": "NO_OA_PDF" if not url else "PENDING",
            "filename": "",
            "sha256": "",
            "bytes": 0,
            "error": "",
        }
        if url:
            temporary = args.output_dir / f"candidate_{index:03d}.pdf.part"
            try:
                digest, size = download_pdf(url, temporary)
                if digest in known_hashes:
                    temporary.unlink(missing_ok=True)
                    record["status"] = "DUPLICATE_PDF"
                    record["sha256"] = digest
                    record["bytes"] = size
                else:
                    while any(args.pdf_dir.glob(f"{next_id}-*.pdf")):
                        next_id += 1
                    filename = f"{next_id}-{safe_name(row.get('title', ''))}.pdf"
                    destination = args.pdf_dir / filename
                    temporary.replace(destination)
                    known_hashes.add(digest)
                    record.update(
                        {
                            "paper_id": next_id,
                            "status": "DOWNLOADED",
                            "filename": filename,
                            "sha256": digest,
                            "bytes": size,
                        }
                    )
                    next_id += 1
            except Exception as exc:
                temporary.unlink(missing_ok=True)
                record["status"] = "DOWNLOAD_FAILED"
                record["error"] = f"{type(exc).__name__}: {exc}"
        manifest.append(record)
        atomic_json(manifest_path, manifest)
        print(
            f"{index}/{len(rows)} {record['status']} {doi}",
            flush=True,
        )
        time.sleep(args.delay)

    write_csv(args.output_dir / "download_manifest.csv", manifest)
    counts: dict[str, int] = {}
    for item in manifest:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    atomic_json(
        args.output_dir / "download_summary.json",
        {
            "task": "TC_OA_DOWNLOAD_101_PLUS_01",
            "shortlist_count": len(rows),
            "status_counts": counts,
            "llm_called": False,
            "paywall_bypassed": False,
            "pdf_directory": str(args.pdf_dir.resolve()),
        },
    )
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
