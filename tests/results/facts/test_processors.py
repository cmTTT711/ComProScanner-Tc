from dataclasses import replace

import pytest

from comproscanner.results.facts import (
    Fact,
    FactProcessor,
    FactValue,
    MaterialParserAPINormalizer,
)


class StubNormalizer:
    def normalize(self, material):
        assert material == "bismuth ferrite (BFO)"
        return "BiFeO3", "BiFeO3"


def test_fact_processor_keeps_reported_material_and_adds_normalized_identity():
    source = Fact(
        "paper_001",
        "Tc",
        "bismuth ferrite (BFO)",
        "",
        "",
        FactValue.from_raw(1103, "K"),
        ("text_1",),
    )
    result = FactProcessor(StubNormalizer()).process(source)
    assert result.material_reported == "bismuth ferrite (BFO)"
    assert result.material_normalized == "BiFeO3"
    assert result.material_identity_key == "BiFeO3"


def test_material_parser_api_normalizer_is_injectable_and_preserves_reported_name():
    source = Fact(
        "paper_001",
        "Tc",
        "bismuth ferrite (BFO)",
        "",
        "",
        FactValue.from_raw(1103, "K"),
        ("text_1",),
    )
    normalizer = MaterialParserAPINormalizer(lambda material: "BiFeO3")
    result = FactProcessor(normalizer).process(source)
    assert result.material_reported == "bismuth ferrite (BFO)"
    assert result.material_normalized == "BiFeO3"


def test_material_parser_api_failure_falls_back_without_losing_fact():
    def unavailable(material):
        raise TimeoutError

    assert MaterialParserAPINormalizer(unavailable).normalize("BiFeO3") == (
        "BiFeO3",
        "BiFeO3",
    )


def make_fact(material="BiFeO3", **kwargs):
    return Fact(
        "paper_001",
        "Tc",
        material,
        material,
        material,
        FactValue.from_raw(1103, "K"),
        ("text_1",),
        **kwargs,
    )


def stub_parser_http(monkeypatch, payload, status=200):
    import requests

    class Response:
        status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(response=self)

        def json(self):
            return payload

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: Response())


def test_service_503_preserves_fact_and_records_status_without_caching_failure(
    monkeypatch,
):
    source = make_fact()
    normalizer = MaterialParserAPINormalizer()
    stub_parser_http(monkeypatch, None, status=503)
    failed = FactProcessor(normalizer).process(source)
    assert failed == replace(
        source, processing_issues=("material_normalization_failed: HTTP 503",)
    )

    stub_parser_http(monkeypatch, [[{"resolvedFormulas": [{"rawValue": "BiFeO3"}]}]])
    assert FactProcessor(normalizer).process(source) == source


@pytest.mark.parametrize(
    "payload",
    [[], [[{"resolvedFormulas": []}]], [[{"resolvedFormulas": [{"rawValue": " "}]}]]],
)
def test_empty_service_result_is_reviewable_and_keeps_original_fact(
    monkeypatch, payload
):
    source = make_fact("sample BFO")
    stub_parser_http(monkeypatch, payload)
    result = FactProcessor(MaterialParserAPINormalizer()).process(source)
    assert result == replace(
        source, processing_issues=("material_normalization_empty",)
    )


@pytest.mark.parametrize(
    "payload",
    [
        [[{"resolvedFormulas": [{"rawValue": "BiFeO3"}, {"rawValue": "BaTiO3"}]}]],
        [
            [{"resolvedFormulas": [{"rawValue": "BiFeO3"}]}],
            [{"resolvedFormulas": [{"rawValue": "BaTiO3"}]}],
        ],
    ],
)
def test_multiple_resolved_materials_never_silently_select_first(monkeypatch, payload):
    source = make_fact("BiFeO3 / BaTiO3 composite")
    stub_parser_http(monkeypatch, payload)
    result = FactProcessor(MaterialParserAPINormalizer()).process(source)
    assert result.material_normalized == source.material_reported
    assert result.material_identity_key == source.material_reported
    assert result.fact_value == source.fact_value
    assert result.evidence_ids == source.evidence_ids
    assert result.processing_issues == (
        "material_normalization_ambiguous: BiFeO3 | BaTiO3",
    )


def test_complex_formula_definitions_reach_resolver_and_reported_text_is_retained():
    reported = "(1-x)BiFeO3-x(Ba1-yCay)TiO3, x=0.26, y=0.15"
    normalized = "0.74BiFeO3-0.26(Ba0.85Ca0.15)TiO3"
    calls = []

    def resolve(material):
        calls.append(material)
        return normalized

    source = make_fact(reported, conditions={"sample_state": "ceramic"})
    processor = FactProcessor(MaterialParserAPINormalizer(resolve))
    result = processor.process(source)
    assert result == replace(
        source, material_normalized=normalized, material_identity_key=normalized
    )
    assert processor.process(source) == result
    assert calls == [reported]


def test_default_identity_preserves_complex_material_values_conditions_and_issues():
    source = make_fact(
        "0.66BaTiO3–0.33CoFe2O4",
        conditions={"microstructure": "randomly mixed", "pressure": 0},
        processing_issues=("source_uncertain",),
    )
    assert FactProcessor().process(source) == source


def test_third_party_normalizer_exception_does_not_lose_fact():
    class BrokenNormalizer:
        def normalize(self, material):
            raise RuntimeError("do not expose connection details")

    source = make_fact()
    assert FactProcessor(BrokenNormalizer()).process(source) == replace(
        source, processing_issues=("material_normalization_failed: RuntimeError",)
    )


def test_third_party_empty_identity_falls_back_to_reported_material():
    class EmptyNormalizer:
        def normalize(self, material):
            return "", ""

    source = make_fact()
    assert FactProcessor(EmptyNormalizer()).process(source) == replace(
        source, processing_issues=("material_normalization_empty",)
    )


def test_preset_validation_only_adds_issues_and_treats_zero_as_present():
    source = make_fact(conditions={"pressure": 0, "method": " "})
    processor = FactProcessor(
        allowed_units=("eV",), required_conditions=("pressure", "method", "frequency")
    )
    result = processor.process(source)
    assert result == replace(
        source,
        processing_issues=(
            "unsupported_unit: K",
            "missing_condition: method",
            "missing_condition: frequency",
        ),
    )
    assert processor.process(result) == result


def test_malformed_parser_payload_is_reviewable(monkeypatch):
    source = make_fact()
    stub_parser_http(monkeypatch, {"unexpected": "response"})
    result = FactProcessor(MaterialParserAPINormalizer()).process(source)
    assert result == replace(
        source, processing_issues=("material_normalization_failed: ValueError",)
    )
