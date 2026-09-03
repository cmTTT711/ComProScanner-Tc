"""Registry describing how raw literature sources enter the common pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArticleSource:
    name: str
    raw_format: str
    processor: str
    network_required: bool
    credential_env: tuple[str, ...] = ()
    optional_credential_env: tuple[str, ...] = ()


class ArticleSourceRegistry:
    def __init__(self):
        self._sources: dict[str, ArticleSource] = {}

    def register(self, source: ArticleSource) -> None:
        if source.name in self._sources:
            raise ValueError(f"Article source already registered: {source.name}")
        self._sources[source.name] = source

    def get(self, name: str) -> ArticleSource:
        try:
            return self._sources[name]
        except KeyError as exc:
            raise KeyError(f"Unknown article source: {name}") from exc

    def list(self) -> tuple[ArticleSource, ...]:
        return tuple(self._sources[name] for name in sorted(self._sources))


def default_source_registry() -> ArticleSourceRegistry:
    registry = ArticleSourceRegistry()
    for source in (
        ArticleSource("manual_pdf", "pdf", "PDFsProcessor", False),
        ArticleSource("downloaded_pdf", "pdf", "PDFsProcessor", False),
        ArticleSource(
            "elsevier", "xml", "ElsevierProcessor", True, ("SCOPUS_API_KEY",)
        ),
        ArticleSource(
            "springer",
            "jats_xml",
            "SpringerProcessor",
            True,
            ("SPRINGER_OPENACCESS_API_KEY",),
            ("SPRINGER_TDM_API_KEY",),
        ),
        ArticleSource("wiley", "pdf", "WileyProcessor", True, ("WILEY_API_KEY",)),
        ArticleSource("iop", "jats_xml", "IOPProcessor", False),
    ):
        registry.register(source)
    return registry
