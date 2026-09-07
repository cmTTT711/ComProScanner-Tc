"""Preset-only extension and early configuration checks; no external calls."""

from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys

import pytest

from comproscanner.presets import get_preset, list_presets, register_preset


def test_band_gap_is_a_complete_independent_property():
    preset = get_preset("band_gap")
    preset.validate()
    assert preset.main_extraction_keyword == "band gap"
    assert preset.allowed_units == ("eV",)
    assert preset.required_conditions == ("determination_method",)
    assert "optical" in preset.extraction_instructions
    assert "computational" in preset.extraction_instructions
    assert any(example["facts"] == [] for example in preset.examples)
    assert "Curie" not in repr(preset)


def test_new_definition_file_is_discovered_without_editing_registry(
    tmp_path, monkeypatch
):
    import comproscanner.presets as package

    (tmp_path / "test_property.py").write_text(
        "from dataclasses import replace\n"
        "from .band_gap import get_preset_definition as band_gap\n"
        "def get_preset_definition():\n"
        "    return replace(band_gap(), name='test_property', "
        "main_extraction_keyword='test property')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(package, "__path__", [*package.__path__, str(tmp_path)])
    monkeypatch.delitem(
        sys.modules, "comproscanner.presets.test_property", raising=False
    )
    assert "test_property" in list_presets()
    assert "comproscanner.presets.test_property" not in sys.modules
    try:
        assert get_preset("test_property").main_extraction_keyword == "test property"
    finally:
        sys.modules.pop("comproscanner.presets.test_property", None)


def test_manual_registration_remains_available(monkeypatch):
    from comproscanner.presets import registry

    monkeypatch.setattr(registry, "_REGISTRY", {})
    register_preset(
        "custom_property",
        lambda: replace(get_preset("band_gap"), name="custom_property"),
    )
    assert "custom_property" in list_presets()
    assert get_preset("custom_property").name == "custom_property"
    with pytest.raises(ValueError, match="already registered"):
        register_preset("custom_property", lambda: None)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"identifier_query": ""}, "identifier_query"),
        ({"extraction_instructions": " "}, "extraction_instructions"),
        ({"retrieval_queries": ()}, "retrieval_queries"),
        ({"allowed_units": ()}, "allowed_units"),
        ({"property_keywords": {"unknown": ["band gap"]}}, "supported keyword"),
        ({"property_keywords": {"exact_keywords": "band gap"}}, "exact_keywords"),
        (
            {"property_keywords": {"candidate_patterns": ["band gap"]}},
            "candidate pattern",
        ),
        ({"property_keywords": {"regex_keywords": ["["]}}, "Invalid preset regex"),
        ({"text_candidate_patterns": ("[",)}, "Invalid preset regex"),
        ({"evidence_providers": ("missing",)}, "Unknown evidence provider"),
        ({"evidence_providers": ()}, "evidence_providers"),
        ({"evidence_providers": ("rule_text", "rule_text")}, "duplicates"),
        ({"required_conditions": ("",)}, "required_conditions"),
        ({"examples": ("bad example",)}, "examples"),
    ],
)
def test_invalid_preset_fails_before_execution(changes, message):
    with pytest.raises(ValueError, match=message):
        replace(get_preset("band_gap"), **changes).validate()


def test_unknown_preset_reports_choices():
    with pytest.raises(KeyError, match="Available:.*band_gap.*curie_temperature"):
        get_preset("does_not_exist")


def test_factory_errors_are_not_relabelled_as_unknown_preset(monkeypatch):
    from comproscanner.presets import registry

    def broken_factory():
        raise KeyError("missing scientific setting")

    monkeypatch.setattr(registry, "_REGISTRY", {"broken": broken_factory})
    with pytest.raises(KeyError, match="missing scientific setting"):
        get_preset("broken")


def test_cli_help_and_listing_do_not_import_model_dependencies():
    root = Path(__file__).resolve().parents[2]
    script = """
import importlib.abc
import sys
class BlockHeavyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'crewai', 'litellm', 'torch', 'transformers', 'chromadb'}:
            raise AssertionError('Unexpected heavyweight import: ' + fullname)
sys.meta_path.insert(0, BlockHeavyImports())
from comproscanner.presets import get_preset, list_presets
assert 'band_gap' in list_presets()
assert 'comproscanner.presets.band_gap' not in sys.modules
assert get_preset('band_gap').allowed_units == ('eV',)
from comproscanner.cli.main import main
assert main(['presets']) == 0
try:
    main(['--help'])
except SystemExit as exc:
    assert exc.code == 0
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root / "src")
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
