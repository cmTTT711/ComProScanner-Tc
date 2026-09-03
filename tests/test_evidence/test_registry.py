import pytest

from comproscanner.evidence import EvidenceProviderRegistry


def test_provider_registry_is_explicit_and_rejects_duplicates():
    registry = EvidenceProviderRegistry()
    registry.register("rule", lambda value: value)
    assert registry.create("RULE", 3) == 3
    assert registry.names() == ("rule",)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("rule", object)
