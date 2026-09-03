"""Literature discovery, download and corpus storage boundaries."""

from .storage import CorpusLayout, DownloadSource
from .io import atomic_csv, atomic_json, normalize_doi, read_csv, safe_filename
from .scopus import ScopusSearch, discover_scopus, parse_scopus_entry
from .oa import (
    download_validated_pdf,
    existing_pdf_hashes,
    hash_file,
    resolve_openalex_urls,
    resolve_semantic_scholar,
)

__all__ = [
    "CorpusLayout",
    "DownloadSource",
    "ScopusSearch",
    "atomic_csv",
    "atomic_json",
    "discover_scopus",
    "download_validated_pdf",
    "existing_pdf_hashes",
    "hash_file",
    "normalize_doi",
    "parse_scopus_entry",
    "read_csv",
    "resolve_openalex_urls",
    "resolve_semantic_scholar",
    "safe_filename",
]
