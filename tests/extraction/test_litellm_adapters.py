from types import SimpleNamespace
from unittest.mock import patch

from comproscanner.extraction.litellm_adapters import (
    LiteLLMEvidenceExtractor,
    LiteLLMEvidenceIdentifier,
    ModelSettings,
)
from comproscanner.evidence import Evidence, EvidenceType, RetrievalMethod


def evidence():
    return Evidence(
        evidence_id="e1",
        document_id="paper_001",
        target_property="tc",
        source_type=EvidenceType.TEXT,
        source_id="chunk_1",
        content="BiFeO3 has a Curie temperature of 1103 K.",
        retrieval_methods=(RetrievalMethod("rule"),),
    )


def response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@patch("litellm.completion")
def test_identifier_requires_structured_yes_no(mock_completion):
    mock_completion.return_value = response('{"answer":"yes"}')
    result = LiteLLMEvidenceIdentifier(ModelSettings("qwen"), "Tc policy").identify(
        evidence()
    )
    assert result.accepted is True


@patch("litellm.completion")
def test_extractor_returns_facts_and_raw_response(mock_completion):
    mock_completion.return_value = response(
        '{"facts":[{"material_reported":"BiFeO3","property":"Tc",'
        '"value":1103,"unit":"K","qualifier":null,"conditions":{}}]}'
    )
    result = LiteLLMEvidenceExtractor(ModelSettings("deepseek"), "Tc policy").extract(
        evidence()
    )
    assert result["facts"][0]["value"] == 1103
    assert "raw_response" in result
