"""Small explicit registry for optional evidence providers."""

from __future__ import annotations

from collections.abc import Callable


class EvidenceProviderRegistry:
    def __init__(self):
        self._factories: dict[str, Callable] = {}

    def register(self, name: str, factory: Callable) -> None:
        key = name.strip().casefold()
        if not key:
            raise ValueError("Provider name cannot be empty")
        if key in self._factories:
            raise ValueError(f"Evidence provider already registered: {key}")
        self._factories[key] = factory

    def create(self, name: str, *args, **kwargs):
        key = name.strip().casefold()
        if key not in self._factories:
            available = ", ".join(self.names()) or "<none>"
            raise KeyError(f"Unknown evidence provider '{name}'. Available: {available}")
        return self._factories[key](*args, **kwargs)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))
