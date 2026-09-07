from comproscanner.documents.literature import CorpusLayout, DownloadSource


def test_corpus_layout_separates_manual_downloaded_and_normalized(tmp_path):
    layout = CorpusLayout.from_root(tmp_path / "pdfs")
    paths = layout.initialize()

    assert layout.manual in paths
    assert layout.downloaded_from(DownloadSource.OPENALEX) in paths
    assert layout.normalized in paths
    assert layout.manual != layout.downloaded_from(DownloadSource.OPENALEX)
    assert all(path.is_dir() for path in paths)
