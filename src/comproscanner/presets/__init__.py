"""Property-specific configurations for the generic extraction pipeline."""

from .base import PropertyExtractionPreset
from .curie_temperature import (
    get_curie_temperature_flow_optional_args,
    get_curie_temperature_preset,
    get_curie_temperature_preset_definition,
)
from .registry import get_preset, list_presets, register_preset

register_preset("curie_temperature", get_curie_temperature_preset_definition)

__all__ = [
    "PropertyExtractionPreset",
    "get_curie_temperature_flow_optional_args",
    "get_curie_temperature_preset",
    "get_curie_temperature_preset_definition",
    "get_preset",
    "list_presets",
    "register_preset",
]
