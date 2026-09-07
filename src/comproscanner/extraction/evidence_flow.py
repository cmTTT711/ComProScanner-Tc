"""Simple per-evidence identifier-to-extractor orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from comproscanner.evidence import Evidence
from comproscanner.evidence import EvidenceType


@dataclass(frozen=True)
class EvidenceDecision:
    evidence_id: str
    accepted: bool
    raw_response: str = ""


@dataclass(frozen=True)
class EvidenceExtraction:
    evidence_id: str
    decision: EvidenceDecision
    extracted: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class EvidenceIdentifier(Protocol):
    def identify(self, evidence: Evidence) -> EvidenceDecision: ...


class EvidenceExtractor(Protocol):
    def extract(
        self, evidence: Evidence, *, visual_observation: str | None = None
    ) -> dict[str, Any]: ...


class FigureInterpreter(Protocol):
    """Read pixels for figure Evidence before structured extraction."""

    def interpret(self, evidence: Evidence) -> str: ...


class EvidenceAgentFlow:
    """Run each evidence independently; one failure never stops its siblings."""

    def __init__(
        self,
        identifier: EvidenceIdentifier,
        extractor: EvidenceExtractor,
        figure_interpreter: FigureInterpreter | None = None,
    ):
        self.identifier = identifier
        self.extractor = extractor
        self.figure_interpreter = figure_interpreter

    def run(self, evidence_items: list[Evidence]) -> list[EvidenceExtraction]:
        results: list[EvidenceExtraction] = []
        for evidence in evidence_items:
            try:
                if evidence.source_type is EvidenceType.FIGURE:
                    if self.figure_interpreter is None:
                        raise RuntimeError(
                            "Figure Evidence requires a configured VLM interpreter"
                        )
                    observation = self.figure_interpreter.interpret(evidence)
                    decision = EvidenceDecision(evidence.evidence_id, True, observation)
                    extracted = self.extractor.extract(
                        evidence, visual_observation=observation
                    )
                    results.append(
                        EvidenceExtraction(evidence.evidence_id, decision, extracted)
                    )
                    continue
                decision = self.identifier.identify(evidence)
                if not decision.accepted:
                    results.append(EvidenceExtraction(evidence.evidence_id, decision))
                    continue
                extracted = self.extractor.extract(evidence)
                results.append(
                    EvidenceExtraction(evidence.evidence_id, decision, extracted)
                )
            except Exception as exc:
                fallback = EvidenceDecision(evidence.evidence_id, False)
                results.append(
                    EvidenceExtraction(
                        evidence.evidence_id,
                        fallback,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
        return results
