"""Minimal Curie temperature (Tc) preset for ComProScanner.

This is intentionally NOT a new extraction pipeline. It only supplies the
existing configurable knobs that ComProScanner already exposes:

- main_property_keyword
- main_extraction_keyword
- property_keywords
- materials_data_identifier_query
- expected few-shot examples
- composition extraction/formatting prompt notes

No production code is changed, and no real LLM API is called by importing this
module. Running ``python examples/extract_curie_temperature.py`` is the entry
point for a real extraction run in the next stage.
"""

from __future__ import annotations

from textwrap import dedent

from comproscanner import ComProScanner


MAIN_PROPERTY_KEYWORD = "magnetic"
MAIN_EXTRACTION_KEYWORD = "Curie temperature"

PROPERTY_KEYWORDS = {
    "exact_keywords": [
        "Curie temperature",
        "curie temperature",
        "Curie point",
        "curie point",
        "ferroelectric Curie temperature",
        "ferroelectric curie temperature",
        "ferroelectric Curie point",
        "ferroelectric curie point",
        "ferroelectric transition temperature",
        "ferroelectric to paraelectric phase transition temperature",
        "phase transition temperature, Tc",
        "magnetic Curie temperature",
        "magnetic curie temperature",
    ],
    "substring_keywords": [
        "curie temperature",
        "curie point",
        " tc ",
        " T_C ",
        " t_c ",
    ],
    "regex_keywords": [
        r"\bt[\s_]*c\s*(?:=|:|≈|~|∼)\s*[+-]?\d",
    ],
}

MATERIALS_DATA_IDENTIFIER_QUERY = (
    "Does the current article explicitly report a Curie temperature (Curie point, "
    "Tc, or T_C) for at least one material composition studied in this work? "
    "Answer 'yes' or 'no' with a single word. Do not count temperatures that are "
    "only used as background, only attributed to other publications, or that are "
    "clearly synthesis/annealing/sintering/measurement/Néel/blocking/glass "
    "transition/decomposition temperatures."
)


def get_curie_temperature_flow_optional_args() -> dict:
    """Return the prompt notes and few-shot examples for the Tc extraction flow."""
    composition_property_extraction_agent_notes = [
        "You are extracting the Curie temperature (Tc / T_C / Curie point) "
        "reported for each material composition, not any other temperature.",
        "Do not treat 'Tc' as Curie temperature unless the surrounding context "
        "explicitly identifies it as Curie temperature / Curie point.",
        "Keep the exact composition -> Curie temperature mapping. Do not assign "
        "one composition's Tc to another composition.",
        "If multiple compositions or doping levels are studied, treat them as "
        "distinct compositions and preserve their own Tc values.",
        "Do not invent, estimate, or calculate a Tc value from external knowledge.",
    ]
    composition_property_extraction_task_notes = [
        "Extract the Curie temperature reported for each material composition "
        "studied in the current article.",
        "If variable composition values are explicitly reported, preserve them so "
        "the existing MaterialParserTool variable-composition normalization can "
        "operate later. Example: 'Bi(1-x)NdxFeO3 where x=0.05'.",
        "Do NOT extract temperatures that are clearly synthesis temperatures, "
        "annealing temperatures, sintering temperatures, measurement "
        "temperatures, Néel temperatures, blocking temperatures, glass "
        "transition temperatures, decomposition temperatures, or generic "
        "phase-transition temperatures unless the article explicitly identifies "
        "the value as Curie temperature / Curie point / Tc in the relevant "
        "context.",
        "Do not treat a Curie temperature mentioned only as general background or "
        "attributed exclusively to another publication as a property value of the "
        "material studied in the current work.",
        "If the article does not provide a Curie temperature for a composition, "
        "do not invent one and do not use external scientific knowledge.",
        "Preserve the reported unit exactly. Use 'K' or '°C' as reported; do not "
        "silently convert between units.",
    ]
    composition_property_formatting_agent_notes = [
        "Preserve the composition -> Curie temperature mapping during formatting.",
        "Keep the reported unit (K or °C) unchanged.",
        "Keep the original family field behavior; do not introduce a material, "
        "sample, or phase hierarchy.",
    ]
    composition_property_formatting_task_notes = [
        "Format the extracted Curie temperature data without converting units.",
        "Keep 'compositions_property_values', 'property_unit', and 'family' as the "
        "only composition-data fields.",
        "Do not add evidence, confidence, truth status, judge, or ScientificFact "
        "fields.",
    ]

    expected_composition_property_example = dedent(
        """
        {
          "compositions": {
            "BiFeO3": 1103,
            "Bi0.95Nd0.05FeO3": 1020
          },
          "property_unit": "K",
          "family": "BiFeO3"
        }
        """
    )
    expected_variable_composition_property_example = dedent(
        """
        {
          "compositions": {
            "Bi(1-x)NdxFeO3 where x=0.05": 1020,
            "Bi(1-x)NdxFeO3 where x=0.10": 950
          },
          "property_unit": "K",
          "family": "BiFeO3"
        }
        """
    )

    return {
        "expected_composition_property_example": expected_composition_property_example,
        "expected_variable_composition_property_example": (
            expected_variable_composition_property_example
        ),
        "composition_property_extraction_agent_notes": (
            composition_property_extraction_agent_notes
        ),
        "composition_property_extraction_task_notes": (
            composition_property_extraction_task_notes
        ),
        "composition_property_formatting_agent_notes": (
            composition_property_formatting_agent_notes
        ),
        "composition_property_formatting_task_notes": (
            composition_property_formatting_task_notes
        ),
    }


def get_curie_temperature_preset() -> dict:
    """Return the minimal Tc preset as plain configuration values."""
    return {
        "main_property_keyword": MAIN_PROPERTY_KEYWORD,
        "property_keywords": PROPERTY_KEYWORDS,
        "extraction_kwargs": {
            "main_extraction_keyword": MAIN_EXTRACTION_KEYWORD,
            "is_extract_synthesis_data": False,
            "materials_data_identifier_query": MATERIALS_DATA_IDENTIFIER_QUERY,
            "identifier_context_mode": "full_candidate",
            **get_curie_temperature_flow_optional_args(),
        },
    }


def main() -> None:
    preset = get_curie_temperature_preset()
    scanner = ComProScanner(main_property_keyword=preset["main_property_keyword"])
    scanner.extract_composition_property_data(
        **preset["extraction_kwargs"],
    )


if __name__ == "__main__":
    main()
