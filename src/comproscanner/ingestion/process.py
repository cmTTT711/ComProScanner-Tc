"""Guarded planning and execution for heterogeneous article processors."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Callable

from .registry import ArticleSourceRegistry, default_source_registry

LOCAL_PDF_SOURCES = frozenset({"manual_pdf", "downloaded_pdf"})


@dataclass(frozen=True)
class ArticleProcessingPlan:
    preset: str
    requested_sources: tuple[str, ...]
    processor_sources: tuple[str, ...]
    folder_path: str | None
    doi_count: int
    network_required: bool
    metadata_network_allowed: bool
    missing_credentials: tuple[str, ...]
    optional_credentials_absent: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def read_doi_file(path: str | Path | None) -> list[str] | None:
    """Read a UTF-8 text file containing one DOI per non-comment line."""
    if path is None:
        return None
    source = Path(path).resolve()
    values = []
    seen = set()
    for raw_line in source.read_text(encoding="utf-8-sig").splitlines():
        value = raw_line.strip()
        if not value or value.startswith("#"):
            continue
        if value.lower().startswith("https://doi.org/"):
            value = value[len("https://doi.org/") :]
        if value not in seen:
            seen.add(value)
            values.append(value)
    return values


def build_processing_plan(
    *,
    preset: str,
    sources: list[str],
    folder_path: str | Path | None = None,
    dois: list[str] | None = None,
    execute_network: bool = False,
    registry: ArticleSourceRegistry | None = None,
) -> ArticleProcessingPlan:
    registry = registry or default_source_registry()
    requested = tuple(dict.fromkeys(source.strip().lower() for source in sources))
    if not requested:
        raise ValueError("At least one article source is required")
    definitions = [registry.get(name) for name in requested]
    local = [name for name in requested if name in LOCAL_PDF_SOURCES]
    if len(local) > 1:
        raise ValueError(
            "Process manual_pdf and downloaded_pdf separately so provenance remains clear"
        )
    resolved_folder = None
    if local:
        if folder_path is None:
            raise ValueError(f"--folder is required for source {local[0]}")
        directory = Path(folder_path).resolve()
        if not directory.is_dir():
            raise FileNotFoundError(f"PDF folder does not exist: {directory}")
        resolved_folder = str(directory)
    elif folder_path is not None:
        raise ValueError("--folder is only valid for manual_pdf or downloaded_pdf")

    network_required = any(source.network_required for source in definitions)
    required = {
        variable
        for source in definitions
        for variable in source.credential_env
    }
    optional = {
        variable
        for source in definitions
        for variable in source.optional_credential_env
    }
    missing = tuple(sorted(variable for variable in required if not os.getenv(variable)))
    optional_absent = tuple(
        sorted(variable for variable in optional if not os.getenv(variable))
    )
    processor_sources = tuple(
        dict.fromkeys("pdfs" if name in LOCAL_PDF_SOURCES else name for name in requested)
    )
    return ArticleProcessingPlan(
        preset=preset,
        requested_sources=requested,
        processor_sources=processor_sources,
        folder_path=resolved_folder,
        doi_count=len(dois or []),
        network_required=network_required,
        metadata_network_allowed=bool(execute_network),
        missing_credentials=missing,
        optional_credentials_absent=optional_absent,
    )


def execute_processing_plan(
    plan: ArticleProcessingPlan,
    *,
    property_keywords: dict,
    main_property_keyword: str,
    processing_kwargs: dict | None = None,
    dois: list[str] | None = None,
    save_xml: bool = False,
    save_pdf: bool = False,
    scanner_factory: Callable | None = None,
) -> None:
    if plan.network_required and plan.missing_credentials:
        raise RuntimeError(
            "Missing required credential environment variable(s): "
            + ", ".join(plan.missing_credentials)
        )
    if scanner_factory is None:
        from ..comproscanner import ComProScanner

        scanner_factory = ComProScanner
    scanner = scanner_factory(main_property_keyword=main_property_keyword)
    kwargs = dict(processing_kwargs or {})
    kwargs.update(
        {
            "property_keywords": property_keywords,
            "source_list": list(plan.processor_sources),
            "folder_path": plan.folder_path,
            "doi_list": dois,
            "is_save_xml": save_xml,
            "is_save_pdf": save_pdf,
            "allow_metadata_network": plan.metadata_network_allowed,
        }
    )
    scanner.process_articles(**kwargs)


def format_processing_plan(plan: ArticleProcessingPlan) -> str:
    return json.dumps(plan.to_dict(), ensure_ascii=False, indent=2)
