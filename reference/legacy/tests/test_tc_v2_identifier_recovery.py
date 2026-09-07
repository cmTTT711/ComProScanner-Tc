"""Deterministic regressions for the opt-in Tc v2 identifier recovery."""

import importlib.util
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from comproscanner.extract_flow.main_extraction_flow import DataExtractionFlow
from comproscanner.documents.docling import matches_property_keywords


ROOT = Path(__file__).resolve().parents[1]


def _tc_preset():
    path = ROOT / "examples" / "extract_curie_temperature.py"
    spec = importlib.util.spec_from_file_location("tc_v2_preset", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.get_curie_temperature_preset()


@pytest.mark.parametrize(
    "text",
    [
        "TC = 315 °C",
        "Tc=315 °C",
        "tc = 315 K",
        "T_C = 315 K",
        "T C = 315",
        "Curie temperature is 315 °C",
        "ferroelectric Curie temperature",
        "ferroelectric transition temperature",
    ],
)
def test_tc_prefilter_matches_explicit_tc_forms(text):
    assert matches_property_keywords(text, _tc_preset()["property_keywords"])


@pytest.mark.parametrize(
    "text",
    [
        "sintering temperature = 1100 °C",
        "annealing temperature",
        "measurement temperature",
        "Néel temperature",
        "blocking temperature",
        "phase transition temperature",
    ],
)
def test_tc_prefilter_rejects_generic_non_tc_temperatures(text):
    assert not matches_property_keywords(text, _tc_preset()["property_keywords"])


def test_default_identifier_mode_remains_rag():
    parameter = inspect.signature(DataExtractionFlow.__init__).parameters[
        "identifier_context_mode"
    ]
    assert parameter.default == "rag"


def test_tc_preset_selects_additive_hybrid_identifier_context():
    kwargs = _tc_preset()["extraction_kwargs"]
    assert kwargs["identifier_context_mode"] == "hybrid"
    assert kwargs["identifier_model"] == "openai/qwen-flash"
    assert kwargs["identifier_api_key_env"] == "DASHSCOPE_API_KEY"


def test_full_candidate_preserves_paragraphs_and_tables():
    candidate = (
        "# RESULTS AND DISCUSSION:\nNormal paragraph text.\n\n"
        "| Sample | T C (C) |\n|---|---|\n| A | 123 |"
    )
    flow = DataExtractionFlow(
        doi="10.9999/test",
        main_extraction_keyword="Curie temperature",
        composition_property_text_data=candidate,
        synthesis_text_data="",
        materials_data_identifier_query="Does this contain Tc data?",
        identifier_context_mode="full_candidate",
    )
    assert flow.state.composition_property_text_data == candidate
    assert "Normal paragraph text" in flow.state.composition_property_text_data
    assert "| Sample | T C (C) |" in flow.state.composition_property_text_data


def test_full_candidate_is_passed_to_identifier(monkeypatch):
    captured = {}

    class FakeCrew:
        def kickoff(self, inputs):
            captured["inputs"] = inputs
            return SimpleNamespace(raw='{"answer": "yes"}')

    class FakeIdentifier:
        def __init__(self, **kwargs):
            captured["context"] = kwargs["identifier_context"]

        def crew(self):
            return FakeCrew()

    monkeypatch.setattr(
        "comproscanner.extract_flow.main_extraction_flow.MaterialsDataIdentifierCrew",
        FakeIdentifier,
    )
    candidate = "Paragraph evidence.\n| Sample | Tc |\n| A | 315 |"
    flow = DataExtractionFlow(
        doi="10.9999/test-context",
        main_extraction_keyword="Curie temperature",
        composition_property_text_data=candidate,
        synthesis_text_data="",
        materials_data_identifier_query="Does this contain Tc data?",
        identifier_context_mode="full_candidate",
    )

    assert flow.identify_materials_data_presence() == "yes"
    assert captured["context"] == candidate
    assert captured["inputs"]["identifier_context"] == candidate


def test_tc_output_schema_remains_unchanged():
    example = _tc_preset()["extraction_kwargs"][
        "expected_composition_property_example"
    ]
    assert '"compositions"' in example
    assert '"property_unit"' in example
    assert '"family"' in example
