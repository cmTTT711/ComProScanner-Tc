from comproscanner.facts import Fact, FactProcessor, FactValue


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
