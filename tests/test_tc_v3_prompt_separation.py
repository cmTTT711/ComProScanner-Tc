"""Regressions proving Tc Identifier and Extractor prompts remain separate."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "examples/extract_curie_temperature.py"


def _preset_module():
    spec = importlib.util.spec_from_file_location("tc_prompt_separation", PRESET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_identifier_prompt_remains_short_high_recall_gate():
    module = _preset_module()
    query = module.MATERIALS_DATA_IDENTIFIER_QUERY
    assert "at least one material composition" in query
    for extractor_only_rule in (
        "frequency-dependent Tm",
        "experimentally investigated object",
        "FINAL CHECK",
    ):
        assert extractor_only_rule not in query


def test_extractor_receives_precision_rules_only_in_extraction_notes():
    module = _preset_module()
    args = module.get_curie_temperature_flow_optional_args()
    extraction = " ".join(args["composition_property_extraction_task_notes"])
    formatting = " ".join(args["composition_property_formatting_task_notes"])
    for rule in ("CURRENT WORK", "TC SEMANTICS", "BINDING", "FINAL CHECK"):
        assert rule in extraction
        assert rule not in formatting


def test_extractor_prompt_covers_required_precision_cases():
    module = _preset_module()
    text = " ".join(module.TC_EXTRACTOR_PRECISION_TASK_NOTES)
    for phrase in (
        "cited reference values",
        "normal ferroelectric-to-paraelectric transition",
        "relaxor peak temperatures",
        "frequency-dependent Tm values",
        "sample-local normal Curie/FE-PE facts",
        "measured composite",
        "constituent's background property",
        "exact material-value binding",
    ):
        assert phrase in text
