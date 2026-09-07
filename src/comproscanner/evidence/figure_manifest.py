"""Load original figure files and captions from a sidecar manifest."""

from __future__ import annotations

import json
from pathlib import Path
from comproscanner._paths import resolve_recorded_path

from comproscanner.evidence.providers.figure import FigureUnit


def load_figure_units(manifest_path: str | Path) -> list[FigureUnit]:
    path = resolve_recorded_path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    document_id = str(payload["document_id"])
    units = []
    for item in payload.get("figures", []):
        image_path = resolve_recorded_path(item["path"])
        if not image_path.is_absolute():
            stored_path = image_path
            image_path = path.parent / stored_path
            # Historical processors stored a path relative to their workspace,
            # although the image itself sits beside this manifest. Recover
            # that layout only when the stored article directory agrees.
            if not image_path.is_file() and stored_path.parent.name == path.parent.name:
                sibling = path.parent / stored_path.name
                if sibling.is_file():
                    image_path = sibling
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
