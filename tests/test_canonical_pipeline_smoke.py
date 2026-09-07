"""Small offline acceptance test for the canonical production contracts."""

from comproscanner.results.evaluation import score_exact_facts
from comproscanner.results.facts import Fact, FactValue, merge_facts
from comproscanner.evidence.preparation import EvidencePreparationPipeline
from comproscanner.results import write_review_workbook


def test_article_to_evidence_to_fact_to_review_to_metrics(tmp_path):
    article = {
        "document_id": "1",
        "paper_id": "1",
        "full_text": "BiFeO3 (BFO) has a Curie temperature of 1103 K.",
    }
    preparation = EvidencePreparationPipeline(
        target_property="Tc",
        property_keywords={"exact_keywords": ["Curie temperature"]},
        provider_names=("rule_text",),
    )
    _, evidence = preparation.prepare_all(article)
    assert len(evidence) == 1

    # Deterministic stand-in for an accepted model response: this test never
    # calls an API, but exercises the same Fact boundary used after extraction.
    extracted = Fact(
        document_id="1",
        property_name="Tc",
        material_reported="BiFeO3 (BFO)",
        material_normalized="BiFeO3",
        material_identity_key="BiFeO3",
        fact_value=FactValue.from_raw(1103, "K"),
        evidence_ids=(evidence[0].evidence_id,),
    )
    facts = merge_facts([extracted])
    workbook = write_review_workbook(tmp_path / "review.xlsx", facts, evidence)
    assert workbook.exists()

    gold = [
        {
            "paper_id": 1,
            "property": "Tc",
            "material": "BiFeO3",
            "value": 1103,
            "unit": "K",
            "strict_scoring": True,
        }
    ]
    metrics = score_exact_facts(gold, [facts[0].to_dict()])
    assert (metrics.tp, metrics.fp, metrics.fn) == (1, 0, 0)
