"""Merge processor CSV outputs into the canonical Article CSV contract."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd

from comproscanner.documents.schemas import normalize_legacy_article_frame
from comproscanner.documents.schemas import validate_article_frame
from comproscanner.documents.csv_store import read_csv_sanitizing_nul


def normalize_article_csvs(
    sources: list[str | Path],
    destination: str | Path,
    *,
    source_type: str = "mixed",
    source_root: str | Path | None = None,
) -> Path:
    if not sources:
        raise ValueError("At least one article CSV is required")
    frames = []
    for source in sources:
        path = Path(source).resolve()
        frame = read_csv_sanitizing_nul(str(path))
        frame = normalize_legacy_article_frame(
            frame, source_type=source_type, source_path=str(path)
        )
        if source_root is not None:
            root = Path(source_root).resolve()
            frame["figures_manifest_path"] = frame["figures_manifest_path"].map(
                lambda value: (
                    str((root / str(value)).resolve())
                    if str(value).strip() and not Path(str(value)).is_absolute()
                    else str(value)
                )
            )
        validate_article_frame(frame)
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["document_id"], keep="first")
    validate_article_frame(combined)
    output = Path(destination).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(fd)
    try:
        combined.to_csv(temporary_name, index=False, encoding="utf-8-sig")
        os.replace(temporary_name, output)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return output
