"""Unit/static tests for the minimal Curie temperature (Tc) preset.

These tests do not call any real LLM API. They verify that the Tc preset is a
pure configuration layer on top of the existing ComProScanner single-property
workflow and that the original composition-property schema is untouched.
"""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = REPO_ROOT / "examples" / "extract_curie_temperature.py"


def _load_preset_module():
    spec = importlib.util.spec_from_file_location(
        "extract_curie_temperature", EXAMPLE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preset_constructs_config():
    preset_module = _load_preset_module()
    preset = preset_module.get_curie_temperature_preset()

    assert preset["main_property_keyword"] == "magnetic"
    assert preset["property_keywords"]["exact_keywords"] == [
        "Curie temperature",
        "Curie point",
    ]
    assert (
        preset["extraction_kwargs"]["main_extraction_keyword"]
        == "Curie temperature"
    )
    assert preset["extraction_kwargs"]["is_extract_synthesis_data"] is False
    assert "Curie temperature" in preset["extraction_kwargs"][
        "materials_data_identifier_query"
    ]


def test_preset_prompt_notes_cover_tc_rules():
    preset_module = _load_preset_module()
    args = preset_module.get_curie_temperature_flow_optional_args()
    text = " ".join(
        args["composition_property_extraction_agent_notes"]
        + args["composition_property_extraction_task_notes"]
        + args["composition_property_formatting_agent_notes"]
        + args["composition_property_formatting_task_notes"]
    )

    required_phrases = [
        "Curie temperature",
        "Do not assign one composition's Tc to another composition",
        "sintering temperatures",
        "measurement temperatures",
        "Néel temperatures",
        "general background",
        "do not invent one",
        "do not silently convert",
        "Do not add evidence",
    ]
    for phrase in required_phrases:
        assert phrase in text, f"Missing Tc rule in prompt notes: {phrase!r}"


def test_expected_examples_preserve_original_keys():
    preset_module = _load_preset_module()
    args = preset_module.get_curie_temperature_flow_optional_args()

    for example in (
        args["expected_composition_property_example"],
        args["expected_variable_composition_property_example"],
    ):
        assert '"compositions"' in example
        assert '"property_unit"' in example
        assert '"family"' in example


def test_composition_schema_unchanged():
    extraction_source = (
        REPO_ROOT
        / "src"
        / "comproscanner"
        / "extract_flow"
        / "crews"
        / "composition_crew"
        / "composition_extraction_crew"
        / "composition_extraction_crew.py"
    ).read_text(encoding="utf-8")
    format_source = (
        REPO_ROOT
        / "src"
        / "comproscanner"
        / "extract_flow"
        / "crews"
        / "composition_crew"
        / "composition_format_crew"
        / "composition_format_crew.py"
    ).read_text(encoding="utf-8")

    assert "compositions_property_values: Dict[str, Union[int, float, None]]" in (
        extraction_source
    )
    assert "property_unit: str" in extraction_source
    assert "family: str" in extraction_source
    assert "compositions_property_values: Dict[str, Union[int, float, None]]" in (
        format_source
    )
    assert "property_unit: str" in format_source
    assert "family: str" in format_source

    for source in (extraction_source, format_source):
        assert "ScientificFact" not in source
        assert "evidence" not in source.lower()
        assert "confidence" not in source.lower()


def test_flow_receives_preset_notes_without_llm():
    from comproscanner.extract_flow.main_extraction_flow import DataExtractionFlow

    preset_module = _load_preset_module()
    args = preset_module.get_curie_temperature_flow_optional_args()

    flow = DataExtractionFlow(
        doi="10.test/curie",
        main_extraction_keyword="Curie temperature",
        composition_property_text_data="A material with a Curie temperature.",
        llm=MagicMock(),
        is_extract_synthesis_data=False,
        **args,
    )

    assert flow.state.main_extraction_keyword == "Curie_temperature"
    assert flow.state.is_extract_synthesis_data is False
    assert "Curie temperature" in flow.state.composition_property_extraction_task_note
    assert "Néel" in flow.state.composition_property_extraction_task_note
    assert (
        flow.state.expected_composition_property_example
        == args["expected_composition_property_example"]
    )
    assert (
        flow.state.expected_variable_composition_property_example
        == args["expected_variable_composition_property_example"]
    )


def test_public_api_accepts_curie_preset_without_llm():
    from comproscanner.comproscanner import ComProScanner

    preset_module = _load_preset_module()
    preset = preset_module.get_curie_temperature_preset()
    scanner = ComProScanner(main_property_keyword=preset["main_property_keyword"])

    mock_preparator = MagicMock()
    mock_preparator.get_unprocessed_data.return_value = []

    temp_root = Path(tempfile.mkdtemp(dir=str(REPO_ROOT / "work")))
    try:
        with (
            patch(
                "comproscanner.comproscanner.MatPropDataPreparator",
                return_value=mock_preparator,
            ),
            patch("comproscanner.comproscanner.LLMConfig") as mock_llm_cfg,
            patch("comproscanner.comproscanner.DataCleaner") as mock_cleaner_cls,
        ):
            mock_llm_cfg.return_value.get_llm.return_value = MagicMock()
            mock_cleaner_cls.return_value.get_useful_data.return_value = {}
            scanner.extract_composition_property_data(
                **preset["extraction_kwargs"],
                json_results_file=str(temp_root / "results.json"),
                checked_doi_list_file=str(temp_root / "checked.txt"),
            )

        assert (temp_root / "results.json").exists()
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_general_d33_flow_still_accepts_default_example():
    from comproscanner.extract_flow.main_extraction_flow import DataExtractionFlow

    flow = DataExtractionFlow(
        doi="10.test/d33",
        main_extraction_keyword="d33",
        composition_property_text_data="BaTiO3 has a d33 value.",
        llm=MagicMock(),
    )

    assert flow.state.main_extraction_keyword == "d33"
    assert '"compositions"' in flow.state.expected_composition_property_example
    assert '"property_unit"' in flow.state.expected_composition_property_example
    assert '"family"' in flow.state.expected_composition_property_example
