from unittest.mock import Mock

from comproscanner.agents import EvidenceAgentFlow, EvidenceDecision
from comproscanner.evidence import Evidence, EvidenceType, RetrievalMethod


def evidence(identifier):
    return Evidence(
        evidence_id=identifier,
        document_id="paper_001",
        target_property="tc",
        source_type=EvidenceType.TEXT,
        source_id=identifier,
        content="Original article text.",
        retrieval_methods=(RetrievalMethod("rule"),),
    )


def figure_evidence(identifier="fig1"):
    return Evidence(
        evidence_id=identifier,
        document_id="paper_001",
        target_property="tc",
        source_type=EvidenceType.FIGURE,
        source_id=identifier,
        content="Figure 1. Transition temperature plot.",
        retrieval_methods=(RetrievalMethod("figure_caption_rule"),),
        metadata={"image_path": "figure.png"},
    )


def test_each_evidence_is_identified_and_only_yes_is_extracted():
    identifier = Mock()
    identifier.identify.side_effect = [
        EvidenceDecision("e1", True),
        EvidenceDecision("e2", False),
    ]
    extractor = Mock()
    extractor.extract.return_value = {"facts": [{"value": 400}]}
    result = EvidenceAgentFlow(identifier, extractor).run([evidence("e1"), evidence("e2")])
    assert len(result) == 2
    assert result[0].extracted["facts"][0]["value"] == 400
    assert result[1].extracted == {}
    extractor.extract.assert_called_once()


def test_one_evidence_failure_does_not_stop_remaining_items():
    identifier = Mock()
    identifier.identify.side_effect = [RuntimeError("network"), EvidenceDecision("e2", True)]
    extractor = Mock(return_value={})
    extractor.extract.return_value = {"facts": []}
    result = EvidenceAgentFlow(identifier, extractor).run([evidence("e1"), evidence("e2")])
    assert result[0].error == "RuntimeError: network"
    assert result[1].error is None
    assert extractor.extract.call_count == 1


def test_figure_uses_vlm_then_extractor_without_text_identifier():
    identifier = Mock()
    extractor = Mock()
    extractor.extract.return_value = {"facts": []}
    vision = Mock()
    vision.interpret.return_value = "Visible point at 580 K for sample A."

    result = EvidenceAgentFlow(identifier, extractor, vision).run([figure_evidence()])

    assert result[0].error is None
    identifier.identify.assert_not_called()
    vision.interpret.assert_called_once()
    extractor.extract.assert_called_once_with(
        figure_evidence(), visual_observation="Visible point at 580 K for sample A."
    )


def test_figure_without_vlm_is_a_recorded_error():
    result = EvidenceAgentFlow(Mock(), Mock()).run([figure_evidence()])
    assert "requires a configured VLM" in result[0].error
