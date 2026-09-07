from comproscanner.evidence.chunking import TextChunk
from comproscanner.evidence import TextEvidenceBuilder
from comproscanner.evidence.providers import RuleTextEvidenceProvider
from comproscanner.evidence.text import TextChunkMatch


def chunk():
    return TextChunk(
        chunk_id="paper_001_RESULTS_0001",
        document_id="paper_001",
        section="results_discussion",
        ordinal=1,
        content="BiFeO3 has a Curie temperature of 1103 K.",
        word_count=8,
    )


def test_rule_and_physbert_share_one_text_evidence():
    item = chunk()
    evidence = TextEvidenceBuilder().build(
        chunks=[item],
        matches=[
            TextChunkMatch(item.chunk_id, "rule", {"term": "Curie temperature"}),
            TextChunkMatch(item.chunk_id, "physbert", {"score": 0.82}),
        ],
        target_property="tc",
    )

    assert len(evidence) == 1
    assert evidence[0].content == item.content
    assert [method.provider for method in evidence[0].retrieval_methods] == [
        "rule",
        "physbert",
    ]


def test_rule_provider_selects_canonical_chunk_without_recutting():
    item = chunk()
    matches = RuleTextEvidenceProvider([r"Curie\s+temperature"]).select([item])
    assert [match.chunk_id for match in matches] == [item.chunk_id]


def test_unknown_chunk_match_is_rejected():
    try:
        TextEvidenceBuilder().build(
            chunks=[chunk()],
            matches=[TextChunkMatch("missing", "physbert")],
            target_property="tc",
        )
    except KeyError as exc:
        assert "Unknown canonical chunk" in str(exc)
    else:
        raise AssertionError("Expected an unknown chunk to fail")
