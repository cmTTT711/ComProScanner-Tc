"""Recover free PDF downloads from OpenAlex OA locations after S2 failures."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import quote

import requests

from download_tc_oa_shortlist import atomic_json, download_pdf, safe_name


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    ROOT
    / "outputs"
    / "literature_discovery"
    / "tc_scopus_2020_2026"
    / "oa_downloads"
    / "download_manifest.json"
)
PDF_DIR = ROOT / "pdfs"
USER_AGENT = "ComProScanner academic OA downloader/1.0"


def known_hashes(pdf_dir: Path) -> set[str]:
    result = set()
    for path in pdf_dir.glob("*.pdf"):
        digest = hashlib.sha256()
        try:
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            result.add(digest.hexdigest())
        except OSError:
            pass
    return result


def oa_urls(doi: str) -> list[str]:
    url = "https://api.openalex.org/works/https://doi.org/" + quote(doi, safe="")
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    work = response.json()
    locations = []
    for key in ("best_oa_location", "primary_location"):
        value = work.get(key)
        if isinstance(value, dict):
            locations.append(value)
    locations.extend(x for x in (work.get("locations") or []) if isinstance(x, dict))
    urls = []
    for location in locations:
        value = (location.get("pdf_url") or "").strip()
        if value and value not in urls:
            urls.append(value)
    return urls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--pdf-dir", type=Path, default=PDF_DIR)
    parser.add_argument("--target", type=int, default=101)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    success = sum(1 for item in manifest if str(item.get("status", "")).startswith("DOWNLOADED"))
    used_ids = {int(x["paper_id"]) for x in manifest if x.get("paper_id") is not None}
    next_id = max(used_ids, default=100) + 1
    hashes = known_hashes(args.pdf_dir)
    for index, item in enumerate(manifest, start=1):
        if success >= args.target:
            break
        if item.get("status") not in {"DOWNLOAD_FAILED", "NO_OA_PDF"}:
            continue
        doi = item.get("doi", "")
        try:
            urls = oa_urls(doi)
        except Exception as exc:
            item["openalex_error"] = f"{type(exc).__name__}: {exc}"
            atomic_json(args.manifest, manifest)
            time.sleep(args.delay)
            continue
        downloaded = False
        errors = []
        for source_url in urls:
            temporary = args.manifest.parent / f"openalex_{index:03d}.pdf.part"
            try:
                digest, size = download_pdf(source_url, temporary)
                if digest in hashes:
                    temporary.unlink(missing_ok=True)
                    item["status"] = "DUPLICATE_PDF"
                    item["sha256"] = digest
                    downloaded = True
                    break
                while any(args.pdf_dir.glob(f"{next_id}-*.pdf")):
                    next_id += 1
                filename = f"{next_id}-{safe_name(item.get('title', ''))}.pdf"
                temporary.replace(args.pdf_dir / filename)
                hashes.add(digest)
                item.update(
                    {
                        "paper_id": next_id,
                        "status": "DOWNLOADED_OPENALEX",
                        "filename": filename,
                        "sha256": digest,
                        "bytes": size,
                        "oa_pdf_url": source_url,
                        "error": "",
                    }
                )
                next_id += 1
                success += 1
                downloaded = True
                print(f"OpenAlex recovery: {success}/{args.target} {doi}", flush=True)
                break
            except Exception as exc:
                temporary.unlink(missing_ok=True)
                errors.append(f"{type(exc).__name__}: {exc}")
        if not downloaded:
            item["openalex_status"] = "NO_WORKING_PDF"
            item["openalex_error"] = " | ".join(errors[:3])
        atomic_json(args.manifest, manifest)
        time.sleep(args.delay)
    print(f"Total downloaded OA PDFs: {success}", flush=True)


if __name__ == "__main__":
    main()
