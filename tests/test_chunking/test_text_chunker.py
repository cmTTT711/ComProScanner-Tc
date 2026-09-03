from comproscanner.chunking import TextChunkConfig, TextChunker


def test_chunker_preserves_sections_and_original_paragraph_order():
    chunker = TextChunker(TextChunkConfig(target_words=5, max_words=12, overlap_words=2))
    chunks = chunker.split_article(
        "paper_001",
        {
            "abstract": "First short paragraph.\n\nSecond paragraph reports Tc at 400 K.",
            "conclusion": "Final conclusion text.",
        },
    )

    assert [chunk.section for chunk in chunks] == ["abstract", "conclusion"]
    assert "First short paragraph." in chunks[0].content
    assert "Second paragraph reports Tc at 400 K." in chunks[0].content
    assert chunks[0].chunk_id == "paper_001_ABSTRACT_0001"


def test_long_paragraph_is_split_with_overlap():
    text = " ".join(f"word{index}." for index in range(30))
    chunks = TextChunker(
        TextChunkConfig(target_words=6, max_words=10, overlap_words=2)
    ).split_section("paper_001", "results_discussion", text)

    assert len(chunks) > 1
    assert all(chunk.word_count <= 12 for chunk in chunks)
    assert chunks[0].content.split()[-2:] == chunks[1].content.split()[:2]


def test_nul_is_removed_without_fixed_three_sentence_window():
    chunks = TextChunker().split_section(
        "paper_001", "introduction", "First sentence.\x00 Second sentence."
    )
    assert len(chunks) == 1
    assert "\x00" not in chunks[0].content
