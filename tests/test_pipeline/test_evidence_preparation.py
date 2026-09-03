import pandas as pd

from comproscanner.chunking import TextChunkConfig
from comproscanner.evidence.text import TextChunkMatch
from comproscanner.pipeline import EvidencePreparationPipeline


def pipeline():
    return EvidencePreparationPipeline(
        target_property="tc",
        property_keywords={
            "candidate_patterns": [{"pattern": r"\bCurie temperature\b"}],
            "exact_keywords": [],
            "substring_keywords": [],
            "regex_keywords": [],
        },
        chunk_config=TextChunkConfig(target_words=20, max_words=40, overlap_words=5),
    )


def row():
    return pd.Series(
        {
            "document_id": "paper_001",
            "abstract": "BiFeO3 has a Curie temperature of 1103 K.",
            "introduction": "Unrelated introductory text.",
            "results_discussion": "",
        }
    )


def test_rule_and_vector_matches_share_canonical_chunks():
    chunks, rule_only = pipeline().prepare_text(row())
    matched_chunk = rule_only[0].source_id
    _, combined = pipeline().prepare_text(
        row(),
        vector_matches=[TextChunkMatch(matched_chunk, "physbert", {"score": 0.2})],
    )
    assert len(combined) == 1
    assert [item.provider for item in combined[0].retrieval_methods] == [
        "rule",
        "physbert",
    ]
    assert combined[0].content == chunks[0].content


def test_evidence_providers_can_be_disabled_by_configuration():
    configured = EvidencePreparationPipeline(
        target_property="tc",
        property_keywords={
            "candidate_patterns": [{"pattern": r"\bCurie temperature\b"}],
            "exact_keywords": [], "substring_keywords": [], "regex_keywords": [],
        },
        provider_names=("table",),
    )
    chunks, evidence = configured.prepare_all(row())
    assert chunks
    assert evidence == []


def test_unknown_evidence_provider_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="Unknown Evidence provider"):
        EvidencePreparationPipeline(
            target_property="tc",
            property_keywords={"exact_keywords": ["Tc"]},
            provider_names=("mystery",),
        )
