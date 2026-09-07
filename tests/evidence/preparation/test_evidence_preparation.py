import pandas as pd

from comproscanner.evidence.chunking import TextChunkConfig
from comproscanner.evidence.text import TextChunkMatch
from comproscanner.evidence.preparation import EvidencePreparationPipeline


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
            "exact_keywords": [],
            "substring_keywords": [],
            "regex_keywords": [],
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


def test_full_text_is_the_single_authoritative_text_source():
    configured = EvidencePreparationPipeline(
        target_property="Curie temperature",
        property_keywords={"exact_keywords": ["Curie temperature"]},
        rule_patterns=[r"793\s*K"],
        provider_names=("rule_text",),
    )
    chunks, evidence = configured.prepare_all(
        {
            "document_id": "paper-4",
            "full_text": "CoFe2O4 has a Curie temperature of 793 K.",
            "abstract": "This section intentionally omits the target value.",
        }
    )
    assert len(chunks) == 1
    assert chunks[0].section == "full_text"
    assert len(evidence) == 1
    assert "793 K" in evidence[0].content


def test_terminal_references_are_retained_but_not_selected_as_evidence():
    configured = EvidencePreparationPipeline(
        target_property="Curie temperature",
        property_keywords={"exact_keywords": ["Curie temperature"]},
        provider_names=("rule_text",),
    )
    body = ("Body paragraph without a property value. " * 40).strip()
    full_text = (
        f"{body}\n\n## References\n\n" "[1] BiFeO3 has a Curie temperature of 1103 K."
    )
    chunks, evidence = configured.prepare_all(
        {
            "document_id": "paper-references",
            "full_text": full_text,
        }
    )
    assert any(chunk.section == "references" for chunk in chunks)
    assert any("1103 K" in chunk.content for chunk in chunks)
    assert evidence == []
