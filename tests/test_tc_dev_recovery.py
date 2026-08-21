"""Focused checks for the Tc development execution-recovery layer."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tc_recovery_configuration():
    preset = _load(ROOT / "examples" / "extract_curie_temperature.py", "tc_preset")
    keywords = preset.get_curie_temperature_preset()["property_keywords"]
    runner_source = (ROOT / "scripts" / "run_tc_dev_recovery.py").read_text(
        encoding="utf-8"
    )

    def matches(text):
        return any(
            keyword in text for group in keywords.values() for keyword in group
        )

    assert 'return f"10.9999/local-tc-dev-{paper_id:03d}"' in runner_source
    assert "PDFsProcessor._extract_doi_from_text = _use_local_identity" in runner_source
    assert "get_doi_from_crossref = _no_crossref_identity" in runner_source
    assert matches(
        "The ferroelectric transition temperature shifts with composition."
    )
    assert matches(
        "The ferroelectric to paraelectric phase transition temperature, Tc decreases."
    )
    assert not matches("The sample was measured at a temperature of 300 K.")
    assert "TIMEOUT_SECONDS = 180" in runner_source
    assert "timeout=TIMEOUT_SECONDS" in runner_source
    assert "recover_empty_section_candidate" in runner_source


def test_tc_schema_and_scientific_prompt_remain_unchanged():
    preset = _load(ROOT / "examples" / "extract_curie_temperature.py", "tc_preset_schema")
    args = preset.get_curie_temperature_flow_optional_args()
    example = args["expected_composition_property_example"]
    notes = " ".join(
        args["composition_property_extraction_agent_notes"]
        + args["composition_property_extraction_task_notes"]
    )

    assert '"compositions"' in example
    assert '"property_unit"' in example
    assert '"family"' in example
    assert "Néel temperatures" in notes
    assert "general background" in notes
    assert "do not invent one" in notes
