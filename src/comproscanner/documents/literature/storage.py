"""Stable corpus layout that keeps manual and API-acquired files separate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DownloadSource(StrEnum):
    ELSEVIER = "elsevier"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    OPENALEX = "openalex"
    DIRECT_OA = "direct_oa"


@dataclass(frozen=True)
class CorpusLayout:
    """Resolve source-specific inputs without mixing them with normalized files."""

    root: Path

    @classmethod
    def from_root(cls, root: str | Path) -> "CorpusLayout":
        return cls(Path(root).resolve())

    @property
    def manual(self) -> Path:
        return self.root / "manual"

    @property
    def downloaded(self) -> Path:
        return self.root / "downloaded"

    def downloaded_from(self, source: DownloadSource | str) -> Path:
        return self.downloaded / DownloadSource(source).value

    @property
    def normalized(self) -> Path:
        return self.root / "normalized"

    @property
    def quarantine(self) -> Path:
        return self.root / "quarantine"

    def initialize(self) -> tuple[Path, ...]:
        paths = (
            self.manual,
            *(self.downloaded_from(source) for source in DownloadSource),
            self.normalized,
            self.quarantine,
        )
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
        return paths

    def as_dict(self) -> dict[str, str]:
        return {
            "manual": str(self.manual),
            **{
                f"downloaded_{source.value}": str(self.downloaded_from(source))
                for source in DownloadSource
            },
            "normalized": str(self.normalized),
            "quarantine": str(self.quarantine),
        }
