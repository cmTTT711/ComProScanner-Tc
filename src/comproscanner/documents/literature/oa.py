"""Open-access location resolvers and validated PDF download primitives."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Callable
from urllib.parse import quote

import requests

from comproscanner.documents.literature.io import normalize_doi

USER_AGENT = "ComProScanner academic full-text acquisition/2.0"
S2_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
OPENALEX_WORK_URL = "https://api.openalex.org/works/https://doi.org/"


def resolve_semantic_scholar(
    dois: list[str],
    *,
    api_key: str | None = None,
    session=requests,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, dict]:
    """Resolve OA metadata in batches; an API key is optional."""
    normalized = list(dict.fromkeys(filter(None, map(normalize_doi, dois))))
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    resolved: dict[str, dict] = {}
    fields = "title,externalIds,openAccessPdf,isOpenAccess,year,venue"
    for offset in range(0, len(normalized), 50):
        batch = normalized[offset : offset + 50]
        for attempt in range(6):
            response = session.post(
                S2_BATCH_URL,
                params={"fields": fields},
                headers=headers,
                json={"ids": [f"DOI:{doi}" for doi in batch]},
                timeout=60,
            )
            if response.status_code == 429 or response.status_code >= 500:
                sleeper(min(45.0, max(2.0, 2**attempt)))
                continue
            response.raise_for_status()
            break
        else:
            raise RuntimeError(f"Semantic Scholar batch failed at offset {offset}")
        payload = response.json()
        for doi, paper in zip(batch, payload):
            resolved[doi] = paper if isinstance(paper, dict) else {}
        sleeper(1.0)
    return resolved


def resolve_openalex_urls(doi: str, *, session=requests) -> list[str]:
    """Return unique OA PDF URLs reported by OpenAlex for one DOI."""
    normalized = normalize_doi(doi)
    if not normalized:
        return []
    response = session.get(
        OPENALEX_WORK_URL + quote(normalized, safe=""),
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if response.status_code == 404:
        return []
    response.raise_for_status()
    work = response.json()
    locations = []
    for name in ("best_oa_location", "primary_location"):
        if isinstance(work.get(name), dict):
            locations.append(work[name])
    locations.extend(
        item for item in (work.get("locations") or []) if isinstance(item, dict)
    )
    return list(
        dict.fromkeys(
            str(location.get("pdf_url") or "").strip()
            for location in locations
            if str(location.get("pdf_url") or "").strip()
        )
    )


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def existing_pdf_hashes(directory: str | Path) -> set[str]:
    hashes = set()
    for path in Path(directory).glob("*.pdf"):
        try:
            hashes.add(hash_file(path))
        except OSError:
            continue
    return hashes


def download_validated_pdf(
    url: str,
    temporary_path: str | Path,
    *,
    session=requests,
    minimum_bytes: int = 10_000,
) -> tuple[str, int]:
    """Stream a PDF, validate signature/size, and return SHA-256 plus byte size."""
    temporary = Path(temporary_path)
    temporary.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    first = b""
    try:
        with session.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*;q=0.5"},
            stream=True,
            timeout=(30, 120),
            allow_redirects=True,
        ) as response:
            response.raise_for_status()
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
            raise ValueError("response is not a PDF")
        if size < minimum_bytes:
            raise ValueError(f"PDF is unexpectedly small ({size} bytes)")
        return digest.hexdigest(), size
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
