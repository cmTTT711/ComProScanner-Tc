"""Predictable output layout with atomic JSON writes and protected Gold data."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class RunStore:
    """Write one extraction run without touching Gold or another run."""

    FILES = (
        "run_config.json",
        "manifest.json",
        "predictions.json",
        "failures.json",
        "tool_usage.json",
        "summary.json",
    )

    def __init__(self, outputs_root: str | Path, run_id: str):
        if not run_id.strip() or run_id in {".", ".."}:
            raise ValueError("run_id must be a non-empty directory name")
        if Path(run_id).name != run_id:
            raise ValueError("run_id cannot contain path separators")
        self.outputs_root = Path(outputs_root).resolve()
        self.run_dir = self.outputs_root / "runs" / run_id
        self.papers_dir = self.run_dir / "papers"
        self.evidence_dir = self.run_dir / "evidence"

    def initialize(self) -> Path:
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        return self.run_dir

    def write_json(self, relative_name: str, value: Any) -> Path:
        target = (self.run_dir / relative_name).resolve()
        if self.run_dir.resolve() not in target.parents:
            raise ValueError("Run output must remain inside its run directory")
        if "gold" in {part.casefold() for part in target.parts}:
            raise ValueError("RunStore cannot write Gold data")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary_name, target)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return target
