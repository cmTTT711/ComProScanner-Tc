"""Unit/static tests for the minimal Curie temperature (Tc) preset.

These tests do not call any real LLM API. They verify that the Tc preset is a
pure configuration layer on top of the existing ComProScanner single-property
workflow and that the original composition-property schema is untouched.
"""

from __future__ import annotations

import importlib.util
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
    assert "Curie temperature" in preset["property_keywords"]["exact_keywords"]
    assert "Curie point" in preset["property_keywords"]["exact_keywords"]
    assert (
        preset["extraction_kwargs"]["main_extraction_keyword"]
        == "Curie temperature"
    )
    assert preset["extraction_kwargs"]["is_extract_synthesis_data"] is False
    assert preset["processing_kwargs"]["allow_missing_doi"] is True
    assert preset["extraction_kwargs"]["identifier_context_mode"] == "hybrid"
    assert preset["extraction_kwargs"]["identifier_model"] == "openai/qwen-flash"
    assert preset["extraction_kwargs"]["identifier_api_key_env"] == (
        "DASHSCOPE_API_KEY"
    )
    assert len(preset["extraction_kwargs"]["hybrid_retrieval_queries"]) == 2
    assert "Curie temperature" in preset["extraction_kwargs"][
        "materials_data_identifier_query"
    ]


def test_typed_preset_registry_preserves_runtime_contract():
    from comproscanner.presets import get_preset, list_presets

    definition = get_preset("curie_temperature")
    runtime = definition.to_runtime_dict()

    assert definition.name == "curie_temperature"
    assert "curie_temperature" in list_presets()
    assert "band_gap" in list_presets()
    assert set(runtime) == {
        "main_property_keyword",
        "property_keywords",
        "processing_kwargs",
        "extraction_kwargs",
    }
    assert runtime["extraction_kwargs"]["main_extraction_keyword"] == (
        "Curie temperature"
    )
    assert definition.identifier_query == runtime["extraction_kwargs"][
        "materials_data_identifier_query"
    ]
    assert tuple(runtime["extraction_kwargs"]["hybrid_retrieval_queries"]) == (
        definition.retrieval_queries
    )
    assert not {
        "identifier_model", "identifier_base_url", "identifier_api_key_env"
    }.intersection(runtime["extraction_kwargs"])


def test_tc_scientific_instructions_preserve_validated_prompt():
    from comproscanner.presets import get_preset
    from comproscanner.presets.curie_temperature import (
        MATERIALS_DATA_IDENTIFIER_QUERY,
        get_curie_temperature_flow_optional_args,
    )

    args = get_curie_temperature_flow_optional_args()
    expected = "\n".join(
        str(args[field]).strip()
        for field in (
            "composition_property_extraction_agent_notes",
            "composition_property_extraction_task_notes",
        )
    )
    preset = get_preset("curie_temperature")
    assert preset.extraction_instructions == expected
    assert preset.identifier_query == MATERIALS_DATA_IDENTIFIER_QUERY
    assert preset.text_candidate_patterns == (r"\d", r"[A-Z]{2,}")
    assert preset.retrieval_queries == (
        "Curie temperature Tc material composition",
        "ferroelectric paraelectric phase transition temperature material",
    )
    assert preset.examples == ()


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
        "background or comparison materials",
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


def test_public_api_accepts_curie_preset_without_llm(tmp_path):
    from comproscanner.documents.dispatch import ComProScanner

    preset_module = _load_preset_module()
    preset = preset_module.get_curie_temperature_preset()
    scanner = ComProScanner(main_property_keyword=preset["main_property_keyword"])

    mock_preparator = MagicMock()
    mock_preparator.get_unprocessed_data.return_value = []

    with (
        patch(
            "comproscanner.documents.dispatch.MatPropDataPreparator",
            return_value=mock_preparator,
        ),
        patch("comproscanner.documents.dispatch.LLMConfig") as mock_llm_cfg,
        patch("comproscanner.documents.dispatch.DataCleaner") as mock_cleaner_cls,
    ):
        mock_llm_cfg.return_value.get_llm.return_value = MagicMock()
        mock_cleaner_cls.return_value.get_useful_data.return_value = {}
        scanner.extract_composition_property_data(
            **preset["extraction_kwargs"],
            json_results_file=str(tmp_path / "results.json"),
            checked_doi_list_file=str(tmp_path / "checked.txt"),
        )

    assert (tmp_path / "results.json").exists()


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
