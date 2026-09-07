"""Tests for additive rule + PhysBERT candidate assembly."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from comproscanner.utils.candidate_context import (
    build_hybrid_candidate_context,
    merge_candidate_context,
)
from comproscanner.evidence.rag.config import RAGConfig


def test_merge_keeps_rule_context_and_appends_only_unique_chunks():
    rule = "# RULE CONTEXT\nBiFeO3 has a transition at 1103 K."
    merged = merge_candidate_context(
        rule,
        [
            "BiFeO3 has a transition at 1103 K.",
            "BaTiO3 has a Curie temperature near 393 K.",
            "  BaTiO3   has a Curie temperature near 393 K.  ",
        ],
    )

    assert merged.startswith(rule)
    assert merged.count("## RETRIEVED CHUNK") == 1
    assert "BaTiO3 has a Curie temperature near 393 K." in merged


def test_hybrid_queries_each_semantic_route_and_merges_results():
    manager = MagicMock()
    manager.database_exists.return_value = True
    manager.query_database.side_effect = [
        [(SimpleNamespace(page_content="Curie context"), 0.1)],
        [(SimpleNamespace(page_content="FE-PE context"), 0.2)],
    ]
    config = RAGConfig(rag_top_k=4)

    merged = build_hybrid_candidate_context(
        doi="10.1000/test",
        rule_candidate="Rule context",
        queries=["Curie query", "phase query"],
        rag_config=config,
        vector_db_manager=manager,
    )

    assert "Rule context" in merged
    assert "Curie context" in merged
    assert "FE-PE context" in merged
    assert manager.query_database.call_count == 2
    manager.query_database.assert_any_call(
        db_name="10.1000_test", query="Curie query", top_k=4
    )


def test_missing_vector_database_falls_back_to_rule_candidate():
    manager = MagicMock()
    manager.database_exists.return_value = False

    result = build_hybrid_candidate_context(
        doi="10.1000/test",
        rule_candidate="Complete rule candidate",
        queries=["Tc"],
        vector_db_manager=manager,
    )

    assert result == "Complete rule candidate"
    manager.query_database.assert_not_called()


def test_identifier_uses_dedicated_model_then_falls_back_on_failure(monkeypatch):
    from comproscanner.extract_flow.main_extraction_flow import DataExtractionFlow

    extraction_llm = MagicMock(name="deepseek")
    identifier_llm = MagicMock(name="qwen")
    used_models = []

    class FakeIdentifier:
        def __init__(self, llm=None, **_kwargs):
            self.llm = llm
            used_models.append(llm)

        def crew(self):
            llm = self.llm

            class FakeCrew:
                def kickoff(self, inputs):
                    if llm is identifier_llm:
                        raise RuntimeError("Qwen unavailable")
                    return SimpleNamespace(raw='{"answer": "yes"}')

            return FakeCrew()

    monkeypatch.setattr(
        "comproscanner.extract_flow.main_extraction_flow.MaterialsDataIdentifierCrew",
        FakeIdentifier,
    )
    flow = DataExtractionFlow(
        doi="10.1000/fallback",
        main_extraction_keyword="Curie temperature",
        composition_property_text_data="BiFeO3 has Tc = 1103 K.",
        llm=extraction_llm,
        identifier_llm=identifier_llm,
        identifier_context_mode="full_candidate",
        materials_data_identifier_query="Is there a material-Tc fact?",
    )

    assert flow.identify_materials_data_presence() == "yes"
    assert used_models == [identifier_llm, extraction_llm]
