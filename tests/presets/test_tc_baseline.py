"""Freeze the validated Tc selection and prompt contract during integration."""

import hashlib
import json

from comproscanner.cli.extraction import _scientific_instructions
from comproscanner.presets import get_preset


def test_tc_evidence_contract_matches_pre_integration_baseline():
    preset = get_preset("curie_temperature")
    contract = {
        "identifier_query": preset.identifier_query,
        "extraction_instructions": _scientific_instructions(preset),
        "retrieval_queries": list(preset.retrieval_queries),
        "text_candidate_patterns": list(preset.text_candidate_patterns),
        "property_keywords": preset.property_keywords,
        "evidence_providers": list(preset.evidence_providers),
    }
    encoded = json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
    # Captured from the pre-change source, not generated from the new preset.
    assert hashlib.sha256(encoded).hexdigest() == (
        "69edac2a371405b361f806940572a4e2510ca3e5ecc29cf10c5485a5dc6993be"
    )
