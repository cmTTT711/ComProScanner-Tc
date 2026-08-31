"""Registry for discoverable, reusable property extraction presets."""

from __future__ import annotations

from collections.abc import Callable

from .base import PropertyExtractionPreset

PresetFactory = Callable[[], PropertyExtractionPreset]
_REGISTRY: dict[str, PresetFactory] = {}


def register_preset(name: str, factory: PresetFactory) -> None:
    """Register a preset factory under a stable lowercase name."""
    key = name.strip().lower()
    if not key:
        raise ValueError("Preset registry name cannot be empty")
    if key in _REGISTRY:
        raise ValueError(f"Preset already registered: {key}")
    _REGISTRY[key] = factory


def get_preset(name: str) -> PropertyExtractionPreset:
    """Return a validated preset definition by name."""
    key = name.strip().lower()
    try:
        preset = _REGISTRY[key]()
    except KeyError as exc:
        choices = ", ".join(sorted(_REGISTRY)) or "<none>"
        raise KeyError(f"Unknown preset '{name}'. Available: {choices}") from exc
    preset.validate()
    return preset


def list_presets() -> tuple[str, ...]:
    """List registered preset names in deterministic order."""
    return tuple(sorted(_REGISTRY))
