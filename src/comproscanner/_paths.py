"""Resolve recorded paths after a workspace relocation without rewriting evidence.

Migration entries are local data, optional, and never point into reference code.
New runs record current absolute paths and do not require this mapping.
"""

from pathlib import Path
import json


def resolve_recorded_path(value, *, base=None):
    original = Path(value)
    candidate = (
        (Path(base) / original) if base and not original.is_absolute() else original
    )
    if candidate.exists():
        return candidate
    locations = [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]
    for root in dict.fromkeys(locations):
        manifest = root / "data/path_migrations.json"
        if not manifest.is_file():
            continue
        entries = json.loads(manifest.read_text(encoding="utf-8"))
        text = str(original).replace("\\", "/").rstrip("/")
        for entry in entries:
            prefix = entry["from"].replace("\\", "/").rstrip("/")
            if text.casefold() == prefix.casefold() or text.casefold().startswith(
                prefix.casefold() + "/"
            ):
                target = (
                    root / entry["to"] / text[len(prefix) :].lstrip("/")
                ).resolve()
                if not target.is_relative_to(root / "data"):
                    raise ValueError(
                        "Recorded path migration must remain inside project data"
                    )
                if target.exists():
                    return target
        return candidate
    return candidate
