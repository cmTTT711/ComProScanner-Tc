from unittest.mock import Mock

from comproscanner.evidence.chunking import TextChunk
from comproscanner.evidence.providers import VectorTextEvidenceProvider
from comproscanner.evidence.vector_store import CanonicalChunkVectorStore


def test_vector_store_indexes_and_returns_canonical_chunk_ids():
    manager = Mock()
    manager.query_chunks.return_value = [
        {"chunk_id": "paper_001_RESULTS_0001", "score": 0.25}
    ]
    store = CanonicalChunkVectorStore(manager)
    chunk = TextChunk(
        "paper_001_RESULTS_0001",
        "paper_001",
        "results_discussion",
        1,
        "BiFeO3 has a Curie temperature of 1103 K.",
        8,
    )
    provider = VectorTextEvidenceProvider(store)
    provider.index("paper/001", [chunk])
    matches = provider.select("paper/001", ["Curie temperature"], top_k=3)

    manager.create_chunk_database.assert_called_once_with("paper_001", [chunk])
    manager.query_chunks.assert_called_once_with(
        "paper_001", query="Curie temperature", top_k=3
    )
    assert matches[0].chunk_id == chunk.chunk_id
    assert matches[0].provider == "physbert"
