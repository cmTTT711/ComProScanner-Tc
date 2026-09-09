from dataclasses import replace
import json

import pandas as pd
import pytest

from comproscanner.cli.main import main
from comproscanner.results.facts import (
    ArticleMaterialNormalizer,
    Fact,
    FactProcessor,
    FactValue,
)


def fact(material, document="paper"):
    return Fact(
        document,
        "Curie temperature",
        material,
        material,
        material,
        FactValue.from_raw(367, "K", "~"),
        ("e1",),
        conditions={"pressure": "1 GPa", "sample_state": "HPT"},
    )


def test_same_article_aliases_preserve_values_conditions_and_original_names():
    source = fact("BLFO-MZFO composite HPT")
    normalizer = ArticleMaterialNormalizer(
        {"paper": "Bi0.9La0.1FeO3 (BLFO) and Mn0.6Zn0.3Fe2.1O4 (MZFO)."}
    )
    out = FactProcessor(normalizer).process(source)
    assert out.material_normalized == "Bi0.9La0.1FeO3-Mn0.6Zn0.3Fe2.1O4 composite HPT"
    assert (
        out.material_reported,
        out.fact_value,
        out.conditions,
        out.evidence_ids,
    ) == (
        source.material_reported,
        source.fact_value,
        source.conditions,
        source.evidence_ids,
    )
    assert all(t["document_id"] == "paper" for t in out.material_resolution)
    other = FactProcessor(normalizer).process(replace(source, document_id="other"))
    assert other.material_normalized == source.material_reported


def test_conflicting_definitions_are_not_silently_selected():
    result = FactProcessor(
        ArticleMaterialNormalizer({"paper": "BiFeO3 (BFO). BaFeO3 (BFO)."})
    ).process(fact("BFO"))
    assert result.material_normalized == "BFO"
    assert "material_definition_ambiguous: BFO" in result.processing_issues


def test_sentence_boundary_before_definition_is_not_a_formula_tail():
    text = "Applications include memory devices [15,16]. BiFeO3 (BFO)."
    out = FactProcessor(ArticleMaterialNormalizer({"paper": text})).process(fact("BFO"))
    assert out.material_normalized == "BiFeO3"


def test_ternary_definition_with_range_preserves_outer_composition():
    formula = "0.65BiFeO3-0.35[(1-x)Bi0.5K0.5TiO3-xBaTiO3]"
    text = formula + " (0.0 ≤ x ≤ 1.0) (BF-BKT-BT) solid solutions."
    out = FactProcessor(ArticleMaterialNormalizer({"paper": text})).process(
        fact("BF-BKT-BT (x=0.4)")
    )
    assert out.material_normalized == (
        "0.65BiFeO3-0.35[0.6Bi0.5K0.5TiO3-0.4BaTiO3] (x=0.4)"
    )
    assert "(0.0 ≤ x ≤ 1.0)" in out.material_resolution[0]["source_text"]


def test_separator_free_alias_requires_unambiguous_same_paper_definition():
    text = "0.58BiFeO3-0.42Bi0.5K0.5TiO3 (BF-BKT)."
    out = FactProcessor(ArticleMaterialNormalizer({"paper": text})).process(
        fact("BFBKT crystal")
    )
    assert out.material_normalized == "0.58BiFeO3-0.42Bi0.5K0.5TiO3 crystal"
    conflict = text + " BaTiO3 (BFBKT)."
    out = FactProcessor(ArticleMaterialNormalizer({"paper": conflict})).process(
        fact("BFBKT crystal")
    )
    assert out.material_normalized == "BFBKT crystal"
    assert "material_definition_ambiguous: BFBKT" in out.processing_issues


@pytest.mark.parametrize(
    "text",
    [
        "0.7BiFeO3\x010.3(Ba0.85Ca0.15)TiO3 (BF-BCT)",
        "Broken material + 0.4 wt.% MnO2 (BF-BCT)",
    ],
)
def test_corrupt_or_incomplete_formula_never_replaced_by_its_tail(text):
    result = FactProcessor(ArticleMaterialNormalizer({"paper": text})).process(
        fact("BF-BCT")
    )
    assert result.material_normalized == "BF-BCT"
    assert "material_name_unresolved" in result.processing_issues


def test_complete_parent_and_additive_both_survive_alias_expansion():
    formula = "0.7BiFeO3-0.3(Ba0.85Ca0.15)TiO3+0.4wt.%MnO2"
    result = FactProcessor(
        ArticleMaterialNormalizer({"paper": formula + " (BF-BCT-M)."})
    ).process(fact("BF-BCT-M"))
    assert result.material_normalized == formula


def test_existing_variable_tool_uses_only_this_facts_assignments():
    text = "(1-y)BiFe1-xCrxO3-yBaTi1-xMnxO3 ceramics. Other samples x=0.2, y=0.4."
    result = FactProcessor(ArticleMaterialNormalizer({"paper": text})).process(
        fact("y=0.24, x=0.01")
    )
    assert result.material_normalized.startswith(
        "0.76BiFe0.99Cr0.01O3-0.24BaTi0.99Mn0.01O3"
    )
    assert result.fact_value == fact("x").fact_value


def test_unknown_ternary_alias_cannot_be_replaced_by_nested_binary_subformula():
    text = "0.65BiFeO3-0.35[(1-x)Bi0.5K0.5TiO3-xBaTiO3] ceramics."
    source = fact("BF-BKT-BT (x=0.4)")
    result = FactProcessor(ArticleMaterialNormalizer({"paper": text})).process(source)
    assert result.material_normalized == source.material_reported
    assert "material_parent_unresolved" in result.processing_issues


def test_cli_saved_results_reach_material_tools_without_models(tmp_path, monkeypatch):
    import requests
    import httpx
    from comproscanner.extraction.litellm_adapters import _LiteLLMClient

    def forbidden(*args, **kwargs):
        raise AssertionError("No external calls permitted in material replay")

    monkeypatch.setattr(_LiteLLMClient, "complete", forbidden)
    monkeypatch.setattr(requests, "post", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    source = tmp_path / "old.json"
    source.write_text(json.dumps([fact("BFO").to_dict()]), encoding="utf-8")
    original = source.read_bytes()
    article = tmp_path / "article.csv"
    pd.DataFrame([{"document_id": "paper", "full_text": "BiFeO3 (BFO)."}]).to_csv(
        article, index=False
    )
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            [
                {
                    "evidence_id": "e1",
                    "document_id": "paper",
                    "target_property": "Curie temperature",
                    "source_type": "text",
                    "source_id": "text",
                    "content": "BFO Tc 367 K",
                    "retrieval_methods": [{"provider": "rule_text", "details": {}}],
                }
            ]
        ),
        encoding="utf-8",
    )
    argv = [
        "postprocess-materials",
        "--predictions",
        str(source),
        "--article-csv",
        str(article),
        "--evidence",
        str(evidence),
        "--outputs",
        str(tmp_path),
        "--run-id",
        "recovered",
    ]
    assert main(argv) == 0
    output = json.loads(
        (tmp_path / "runs/recovered/predictions.json").read_text(encoding="utf-8")
    )[0]
    assert output["material_normalized"] == "BiFeO3"
    assert output["material_reported"] == "BFO"
    assert output["fact_value"] == fact("BFO").to_dict()["fact_value"]
    assert output["conditions"] == fact("BFO").conditions
    assert output["material_resolution"]
    assert source.read_bytes() == original
    with pytest.raises(FileExistsError):
        main(argv)


def test_normal_extraction_default_also_runs_material_tools(tmp_path, monkeypatch):
    from comproscanner.extraction.litellm_adapters import _LiteLLMClient

    calls = []

    def complete(self, messages):
        calls.append(messages)
        if "qwen" in self.settings.model:
            return json.dumps({"answer": "yes"})
        return json.dumps(
            {
                "facts": [
                    {
                        "material_reported": "BFO",
                        "property": "Curie temperature",
                        "value": 1100,
                        "unit": "K",
                        "qualifier": "~",
                        "conditions": {},
                    }
                ]
            }
        )

    monkeypatch.setattr(_LiteLLMClient, "complete", complete)
    article = tmp_path / "article.csv"
    pd.DataFrame(
        [
            {
                "document_id": "paper",
                "full_text": "BiFeO3 (BFO) has a Curie temperature of about 1100 K.",
            }
        ]
    ).to_csv(article, index=False)
    assert (
        main(
            [
                "run",
                "--csv",
                str(article),
                "--outputs",
                str(tmp_path),
                "--run-id",
                "normal",
                "--provider",
                "rule_text",
                "--execute-pipeline",
                "--execute-models",
            ]
        )
        == 0
    )
    output = json.loads(
        (tmp_path / "runs/normal/predictions.json").read_text(encoding="utf-8")
    )
    assert len(calls) == 2  # The unchanged identifier/extractor pair; no material LLM.
    assert output[0]["material_reported"] == "BFO"
    assert output[0]["material_normalized"] == "BiFeO3"
    assert output[0]["material_resolution"]
