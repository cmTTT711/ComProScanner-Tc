"""Literature discovery, download and corpus storage boundaries."""

from comproscanner.documents.literature.storage import CorpusLayout
from comproscanner.documents.literature.storage import DownloadSource
from comproscanner.documents.literature.io import atomic_csv
from comproscanner.documents.literature.io import atomic_json
from comproscanner.documents.literature.io import normalize_doi
from comproscanner.documents.literature.io import read_csv
from comproscanner.documents.literature.io import safe_filename
from comproscanner.documents.literature.scopus import ScopusSearch
from comproscanner.documents.literature.scopus import discover_scopus
from comproscanner.documents.literature.scopus import parse_scopus_entry
from comproscanner.documents.literature.oa import download_validated_pdf
from comproscanner.documents.literature.oa import existing_pdf_hashes
from comproscanner.documents.literature.oa import hash_file
from comproscanner.documents.literature.oa import resolve_openalex_urls
from comproscanner.documents.literature.oa import resolve_semantic_scholar

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
