"""Property configuration registry; definitions are loaded on demand."""

from .base import PropertyExtractionPreset
from .registry import get_preset, list_presets, register_preset

__all__ = ["PropertyExtractionPreset", "get_preset", "list_presets", "register_preset"]
