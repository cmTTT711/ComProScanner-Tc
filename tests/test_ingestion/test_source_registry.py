import pytest

from comproscanner.ingestion import default_source_registry


def test_default_sources_are_explicit_and_pluggable():
    registry = default_source_registry()
    assert {source.name for source in registry.list()} == {
        "manual_pdf",
        "downloaded_pdf",
        "elsevier",
        "springer",
        "wiley",
        "iop",
    }
    assert registry.get("wiley").raw_format == "pdf"
    assert registry.get("elsevier").network_required is True
    with pytest.raises(KeyError, match="Unknown article source"):
        registry.get("unknown")
