"""Paragraph-aware, section-preserving article text chunking."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TextChunkConfig:
    """Configuration for canonical chunks shared by rules and vector search."""

    target_words: int = 220
    max_words: int = 360
    overlap_words: int = 60

    def validate(self) -> None:
        if self.target_words <= 0 or self.max_words <= 0:
            raise ValueError("Chunk sizes must be positive")
        if self.target_words > self.max_words:
            raise ValueError("target_words cannot exceed max_words")
        if self.overlap_words < 0 or self.overlap_words >= self.max_words:
            raise ValueError("overlap_words must be between 0 and max_words - 1")


@dataclass(frozen=True)
class TextChunk:
    """One immutable span of source text used by all text retrieval methods."""

    chunk_id: str
    document_id: str
    section: str
    ordinal: int
    content: str
    word_count: int
    page_start: int | None = None
    page_end: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class TextChunker:
    """Build canonical chunks without crossing article-section boundaries."""

    _PARAGRAPH_BREAK = re.compile(r"(?:\r?\n){2,}")
    _SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])")

    def __init__(self, config: TextChunkConfig | None = None):
        self.config = config or TextChunkConfig()
        self.config.validate()

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[ \t]+", " ", text.replace("\x00", "")).strip()

    @staticmethod
    def _words(text: str) -> list[str]:
        return text.split()

    def _split_long_span(self, text: str) -> list[str]:
        sentences = [
            self._normalize(item)
            for item in self._SENTENCE_BREAK.split(text)
            if self._normalize(item)
        ]
        if len(sentences) <= 1:
            words = self._words(text)
            step = self.config.max_words - self.config.overlap_words
            return [
                " ".join(words[start : start + self.config.max_words])
                for start in range(0, len(words), step)
                if words[start : start + self.config.max_words]
            ]

        chunks: list[str] = []
        current: list[str] = []
        for sentence in sentences:
            candidate = " ".join([*current, sentence])
            if current and len(self._words(candidate)) > self.config.max_words:
                chunks.append(" ".join(current))
                overlap: list[str] = []
                overlap_count = 0
                for previous in reversed(current):
                    overlap.insert(0, previous)
                    overlap_count += len(self._words(previous))
                    if overlap_count >= self.config.overlap_words:
                        break
                current = overlap
            current.append(sentence)
        if current:
            chunks.append(" ".join(current))
        return chunks

    def split_section(
        self, document_id: str, section: str, text: str
    ) -> list[TextChunk]:
        """Split one section; chunks never contain text from another section."""

        normalized = self._normalize(str(text or ""))
        if not normalized:
            return []
        paragraphs = [
            self._normalize(item)
            for item in self._PARAGRAPH_BREAK.split(normalized)
            if self._normalize(item)
        ]
        spans: list[str] = []
        pending: list[str] = []
        pending_words = 0
        for paragraph in paragraphs:
            count = len(self._words(paragraph))
            if count > self.config.max_words:
                if pending:
                    spans.append("\n\n".join(pending))
                    pending, pending_words = [], 0
                spans.extend(self._split_long_span(paragraph))
                continue
            if pending and pending_words + count > self.config.max_words:
                spans.append("\n\n".join(pending))
                pending, pending_words = [], 0
            pending.append(paragraph)
            pending_words += count
            if pending_words >= self.config.target_words:
                spans.append("\n\n".join(pending))
                pending, pending_words = [], 0
        if pending:
            spans.append("\n\n".join(pending))

        safe_document = re.sub(r"[^A-Za-z0-9]+", "_", document_id).strip("_")
        safe_section = re.sub(r"[^A-Za-z0-9]+", "_", section).strip("_").upper()
        return [
            TextChunk(
                chunk_id=f"{safe_document}_{safe_section}_{ordinal:04d}",
                document_id=document_id,
                section=section,
                ordinal=ordinal,
                content=span,
                word_count=len(self._words(span)),
            )
            for ordinal, span in enumerate(spans, start=1)
        ]

    def split_article(
        self, document_id: str, sections: dict[str, str]
    ) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        for section, text in sections.items():
            chunks.extend(self.split_section(document_id, section, text))
        return chunks
