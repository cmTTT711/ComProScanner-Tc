"""Load original figure files and captions from a sidecar manifest."""

from __future__ import annotations

import json
from pathlib import Path

from .providers.figure import FigureUnit


def load_figure_units(manifest_path: str | Path) -> list[FigureUnit]:
    path = Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    document_id = str(payload["document_id"])
    units = []
    for item in payload.get("figures", []):
        image_path = Path(item["path"])
        if not image_path.is_absolute():
            image_path = path.parent / image_path
        units.append(
            FigureUnit(
                figure_id=str(item["figure_id"]),
                document_id=document_id,
                image_path=str(image_path),
                caption=str(item.get("caption", "")),
                nearby_text=str(item.get("nearby_text", "")),
                section=item.get("section"),
                page=item.get("page"),
            )
        )
    return units
