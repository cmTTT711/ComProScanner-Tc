"""Provider protocol and small matching helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Protocol, TypeVar

T = TypeVar("T")


class EvidenceProvider(Protocol[T]):
    name: str

    def select(self, units: Iterable[T]): ...


def find_patterns(text: str, patterns: Iterable[str]) -> list[str]:
    """Return the supplied regex patterns that match text."""

    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE)]
