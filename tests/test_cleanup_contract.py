"""Behavioral boundaries required by the project cleanup."""

import ast
from dataclasses import replace
import json
from pathlib import Path

import pandas as pd
import pytest

from comproscanner.extraction import litellm_adapters as adapters
from comproscanner.evidence import Evidence, EvidenceType, RetrievalMethod
from comproscanner.presets import get_preset
from comproscanner.cli.extraction import _scientific_instructions
from comproscanner.results.facts import Fact, FactValue, FactProcessor, merge_facts
from comproscanner.results.export import write_results_workbook

ROOT = Path(__file__).resolve().parents[1]


def test_complete_tc_wire_messages_are_unchanged(monkeypatch):
    messages = []

    def complete(self, prompt):
        messages.append(prompt)
        return '{"answer":"yes","facts":[]}'

    monkeypatch.setattr(adapters._LiteLLMClient, "complete", complete)
    preset = get_preset("curie_temperature")
    for kind in ("text", "table", "equation"):
        evidence = Evidence(
            evidence_id="e1",
            document_id="p1",
            target_property="Curie temperature",
            source_type=EvidenceType(kind),
            source_id="s1",
            content="BiFeO3 has Tc ~1103 K.",
            retrieval_methods=(RetrievalMethod("fixture"),),
        )
        adapters.LiteLLMEvidenceIdentifier(
            adapters.ModelSettings("fixture"),
            preset.identifier_query,
            preset.agent_prompts,
        ).identify(evidence)
        adapters.LiteLLMEvidenceExtractor(
            adapters.ModelSettings("fixture"),
            _scientific_instructions(preset),
            preset.agent_prompts,
            preset.fact_fields,
        ).extract(evidence)
    evidence = replace(evidence, source_type=EvidenceType.FIGURE)
    adapters.LiteLLMEvidenceExtractor(
        adapters.ModelSettings("fixture"),
        _scientific_instructions(preset),
        preset.agent_prompts,
        preset.fact_fields,
    ).extract(evidence, visual_observation="Original figure labels: BiFeO3, ~1103 K.")
    expected = json.loads(
        (ROOT / "tests/fixtures/tc_wire_messages.json").read_text(encoding="utf-8")
    )
    assert messages == expected


def test_extra_preset_fields_survive_processing_merge_and_export(tmp_path):
    fact = Fact(
        "p1",
        "band gap",
        "GaN",
        "GaN",
        "GaN",
        FactValue.from_raw(3.4, "eV"),
        ("e1",),
        attributes={"method": "optical"},
    )
    processed = FactProcessor().process(fact)
    merged = merge_facts(
        [processed, replace(processed, attributes={"method": "electrical"})]
    )
    assert len(merged) == 2 and processed.attributes == fact.attributes
    articles = pd.DataFrame(
        [
            {
                "document_id": "p1",
                "doi": "10.test/a",
                "article_title": "Paper title",
                "metadata_json": '{"publisher":"Journal"}',
            }
        ]
    )
    path = write_results_workbook(tmp_path / "predictions.xlsx", merged, articles)
    rows = pd.read_excel(path)
    assert rows["article_title"].tolist() == ["Paper title"] * 2
    assert rows["publisher"].tolist() == ["Journal"] * 2
    assert rows["attribute.method"].nunique() == 2


def test_active_package_has_no_retired_dependencies():
    banned = {"crewai", "crewai_tools", "mysql", "neo4j", "sqlalchemy", "reference"}
    for path in (ROOT / "src/comproscanner").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = (
                [node.module]
                if isinstance(node, ast.ImportFrom)
                else (
                    [n.name for n in node.names] if isinstance(node, ast.Import) else []
                )
            )
            assert not any(
                name and name.split(".")[0] in banned for name in names
            ), path


def test_article_schema_preserves_publisher_metadata():
    from comproscanner.documents.schemas import normalize_legacy_article_frame

    row = normalize_legacy_article_frame(
        pd.DataFrame(
            [
                {
                    "document_id": "p1",
                    "full_text": "Original body",
                    "publication_name": "Journal",
                    "year": 2024,
                }
            ]
        )
    ).iloc[0]
    metadata = json.loads(row.metadata_json)
    assert row.full_text == "Original body"
    assert metadata == {"publication_name": "Journal", "year": "2024"}


def test_preset_controls_model_prompts_and_modality_selection(monkeypatch):
    from comproscanner.presets import register_preset
    from comproscanner.presets._shared import AgentPrompts
    from comproscanner.cli.main import build_parser, _apply_preset_defaults
    from comproscanner.evidence.preparation import EvidencePreparationPipeline

    template = replace(
        get_preset("band_gap"),
        name="test_cleanup_custom",
        models={
            **get_preset("band_gap").models,
            "extractor": {"model": "custom/model", "parameters": {"max_tokens": 256}},
        },
        agent_prompts=replace(
            AgentPrompts(), extractor_system="Custom property extractor"
        ),
        modality_patterns={"table": ("custom marker",)},
    )
    from comproscanner.presets import registry

    monkeypatch.setitem(registry._REGISTRY, template.name, lambda: template)
    args = build_parser().parse_args(
        ["extract", "--run-id", "r1", "--preset", template.name]
    )
    _apply_preset_defaults(args)
    assert args.extractor_model == "custom/model"
    messages = []
    monkeypatch.setattr(
        adapters._LiteLLMClient,
        "complete",
        lambda self, prompt: messages.append(prompt) or '{"facts":[]}',
    )
    e = Evidence(
        "e1",
        "p1",
        "band gap",
        EvidenceType.TABLE,
        "s1",
        "custom marker",
        (RetrievalMethod("fixture"),),
    )
    adapters.LiteLLMEvidenceExtractor(
        adapters.ModelSettings(args.extractor_model), "policy", template.agent_prompts
    ).extract(e)
    assert messages[0][0]["content"] == "Custom property extractor"
    pipeline = EvidencePreparationPipeline(
        target_property="band gap",
        property_keywords=template.property_keywords,
        provider_names=("table",),
        modality_patterns=template.modality_patterns,
    )
    from comproscanner.evidence.providers.table import TableUnit

    unit = TableUnit(
        "t1", "p1", "custom marker", ("material", "value"), (("GaN", "3.4"),)
    )
    assert len(pipeline.table_provider.select([unit], "band gap")) == 1


def test_review_to_gold_requires_decision_and_never_overwrites(tmp_path):
    from comproscanner.results.review import write_review_workbook
    from comproscanner.results.gold import accept_review
    from openpyxl import load_workbook

    e = Evidence(
        "e1",
        "p1",
        "band gap",
        EvidenceType.TEXT,
        "s1",
        "GaN band gap 3.4 eV",
        (RetrievalMethod("fixture"),),
    )
    fact = Fact(
        "p1", "band gap", "GaN", "GaN", "GaN", FactValue.from_raw(3.4, "eV"), ("e1",)
    )
    review = write_review_workbook(tmp_path / "review.xlsx", [fact], [e])
    gold = tmp_path / "gold.json"
    with pytest.raises(ValueError, match="no ACCEPT"):
        accept_review(review, gold)
    workbook = load_workbook(review)
    workbook["facts"]["L2"] = "ACCEPT"
    workbook.save(review)
    accept_review(review, gold)
    result = json.loads(gold.read_text(encoding="utf-8"))
    assert result[0]["evidence_ids"] == ["e1"]
    from comproscanner.results.evaluation import score_exact_facts

    assert score_exact_facts(result, [fact.to_dict()]).f1 == 1
    with pytest.raises(FileExistsError):
        accept_review(review, gold)
