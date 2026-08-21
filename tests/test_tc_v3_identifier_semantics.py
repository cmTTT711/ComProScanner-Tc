"""Static regressions for the full-candidate Identifier semantic gate."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TASKS_SOURCE = (
    ROOT
    / "src/comproscanner/extract_flow/crews/materials_data_identifier_crew/config/tasks.yaml"
).read_text(encoding="utf-8")
TASKS = " ".join(
    yaml.safe_load(TASKS_SOURCE)["identify_materials_data_from_context"][
        "description"
    ].split()
)
CREW = (
    ROOT
    / "src/comproscanner/extract_flow/crews/materials_data_identifier_crew/materials_data_identifier_crew.py"
).read_text(encoding="utf-8")

SEMANTIC_FIXTURES = {
    "shared_value_series": ("x=0.1 through x=0.5 current composites share a 150 C FE-PE transition", "YES"),
    "table_tm_with_target_semantics": ("85BPF Tm=151 C; local text identifies the FE-PE transition", "YES"),
    "normal_fe_among_relaxors": ("x=.01 has a normal 853.1 K FE-PE transition; x=.03/.05 are relaxors", "YES"),
    "cited_background": ("BiFeO3 has Tc 1103 K [reference]; current composite reports no Tc", "NO"),
    "curie_weiss": ("The Curie-Weiss temperature is 450 K", "NO"),
    "neel": ("The Neel temperature is 640 K", "NO"),
    "generic_tm": ("A dielectric maximum Tm occurs at 320 C without target semantics", "NO"),
    "sintering": ("The sample was sintered at 900 C", "NO"),
    "constituent_background": ("BaTiO3 has known Tc 120 C but the current composite has no transition measurement", "NO"),
}


def test_identifier_is_an_existence_gate_not_an_extractor():
    assert "semantic existence gate" in TASKS
    assert "not the final extraction step" in TASKS
    assert "Do not require final composition normalization" in CREW


def test_identifier_allows_shared_value_series():
    assert "expand one shared value across multiple current-work samples" in TASKS


def test_identifier_allows_locally_valid_fact_in_mixed_context():
    assert "Evaluate facts locally" in TASKS
    assert "one valid normal transition is sufficient" in TASKS


def test_identifier_requires_tm_target_semantics():
    assert "Tm by itself is not sufficient" in TASKS
    assert "explicitly identifies it as the" in TASKS
    assert "target transition" in TASKS


def test_identifier_preserves_negative_semantic_guards():
    for phrase in (
        "cited or background facts",
        "constituent background properties",
        "Curie-Weiss",
        "Neel",
        "blocking",
        "spin-glass",
        "synthesis or measurement temperatures",
        "generic dielectric maximum/Tm",
        "unrelated phase transitions",
    ):
        assert phrase in TASKS


def test_semantic_fixture_expectations_cover_required_cases():
    assert [expected for _, expected in SEMANTIC_FIXTURES.values()].count("YES") == 3
    assert [expected for _, expected in SEMANTIC_FIXTURES.values()].count("NO") == 6
