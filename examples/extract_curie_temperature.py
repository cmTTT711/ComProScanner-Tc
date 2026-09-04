"""Compatibility example exposing the frozen Tc preset.

New batch execution should use ``comproscanner run`` as documented in this
directory's README. This module remains because downstream users and regression
tests import its preset constants.
"""

from comproscanner import ComProScanner
from comproscanner.presets.curie_temperature import (
    MAIN_EXTRACTION_KEYWORD,
    MAIN_PROPERTY_KEYWORD,
    MATERIALS_DATA_IDENTIFIER_QUERY,
    PROPERTY_KEYWORDS,
    TC_EXTRACTOR_PRECISION_TASK_NOTES,
    get_curie_temperature_flow_optional_args,
    get_curie_temperature_preset,
)

__all__ = [
    "get_curie_temperature_flow_optional_args",
    "get_curie_temperature_preset",
    "MAIN_EXTRACTION_KEYWORD",
    "MAIN_PROPERTY_KEYWORD",
    "MATERIALS_DATA_IDENTIFIER_QUERY",
    "PROPERTY_KEYWORDS",
    "TC_EXTRACTOR_PRECISION_TASK_NOTES",
]


def main() -> None:
    preset = get_curie_temperature_preset()
    scanner = ComProScanner(main_property_keyword=preset["main_property_keyword"])
    scanner.extract_composition_property_data(**preset["extraction_kwargs"])


if __name__ == "__main__":
    main()
