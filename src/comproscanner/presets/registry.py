"""Registry for discoverable, reusable property extraction presets."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pkgutil import iter_modules
import re

from comproscanner.presets.base import PropertyExtractionPreset

PresetFactory = Callable[[], PropertyExtractionPreset]
_REGISTRY: dict[str, PresetFactory] = {}


def _module_names() -> set[str]:
    """Find definition files without importing optional model dependencies."""
    package = import_module(__package__)
    return {
        module.name
        for module in iter_modules(package.__path__)
        if not module.ispkg
        and not module.name.startswith("_")
        and module.name not in {"base", "registry"}
    }


def _key(name: str) -> str:
    key = name.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
        raise ValueError("Preset name must be a lowercase Python module name")
    return key


def register_preset(name: str, factory: PresetFactory) -> None:
    """Register a preset factory under a stable lowercase name."""
    key = _key(name)
    if not callable(factory):
        raise ValueError("Preset factory must be callable")
    if key in _REGISTRY or key in _module_names():
        raise ValueError(f"Preset already registered: {key}")
    _REGISTRY[key] = factory


def get_preset(name: str) -> PropertyExtractionPreset:
    """Return a validated preset definition by name."""
    key = _key(name)
    if key in _REGISTRY:
        factory = _REGISTRY[key]
    elif key in _module_names():
        module = import_module(f"{__package__}.{key}")
        factory = getattr(module, "get_preset_definition", None)
        if not callable(factory):
            raise ValueError(
                f"Preset module {key!r} must define get_preset_definition()"
            )
    else:
        choices = ", ".join(list_presets()) or "<none>"
        raise KeyError(f"Unknown preset '{name}'. Available: {choices}")
    preset = factory()
    if not isinstance(preset, PropertyExtractionPreset):
        raise ValueError(f"Preset factory {key!r} must return PropertyExtractionPreset")
    if preset.name != key:
        raise ValueError(
            f"Preset name {preset.name!r} must match registered/module name {key!r}"
        )
    preset.validate()
    return preset


def list_presets() -> tuple[str, ...]:
    """List definition modules and explicit registrations without loading them."""
    return tuple(sorted(_module_names() | _REGISTRY.keys()))
