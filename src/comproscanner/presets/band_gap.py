"""Band-gap configuration example; real-paper accuracy is not yet validated.

This module is deliberately limited to scalar, explicitly reported band gaps.
It demonstrates adding an attribute without changing the extraction pipeline.
The examples are synthetic illustrations, not accuracy-validation results.
"""

from __future__ import annotations

from comproscanner.presets.base import PropertyExtractionPreset


def get_preset_definition() -> PropertyExtractionPreset:
    """Describe evidence selection, scientific meaning and review policy."""
    return PropertyExtractionPreset(
        name="band_gap",
        main_property_keyword="electronic",
        main_extraction_keyword="band gap",
        property_keywords={
            "candidate_patterns": [
                {"class": "BAND_GAP", "pattern": r"(?i)\bband[\s-]*gap\b"},
                {
                    "class": "ENERGY_GAP",
                    "pattern": r"(?i)\b(?:optical|electronic|fundamental)\s+(?:energy\s+)?gap\b",
                },
                {
                    "class": "EG_VALUE",
                    "pattern": r"(?i)(?<![a-z])E\s*_?\s*g\s*(?:[=:≈~]|is|of)\s*\d",
                },
            ],
            "exact_keywords": ["band gap", "bandgap", "optical gap", "electronic gap"],
            "substring_keywords": ["band-gap", "energy gap"],
            "regex_keywords": [r"(?i)\bE\s*_?\s*g\b.{0,60}\beV\b"],
        },
        identifier_query=(
            "Does this evidence explicitly assign a numerical band-gap energy to "
            "an identifiable material? Include optical measurements and computed "
            "electronic gaps, and explicit current-work, comparison or cited-material "
            "statements. Answer yes or no. Exclude absorption wavelengths, emission "
            "peaks, activation energies, exciton binding energies, and offsets between "
            "materials unless an explicit material-to-band-gap value is also given."
        ),
        extraction_instructions=(
            "Extract only explicitly reported scalar band-gap energies with an exact "
            "material-to-value relationship. Include current-work, comparison and "
            "cited-material facts when the evidence states the relationship; do not "
            "supply values from external knowledge. Preserve composition, dopant "
            "concentration, phase, thickness and sample identity when reported. "
            "Keep measured optical gaps and computed electronic/fundamental gaps "
            "as separate records: use conditions.determination_method='optical' "
            "or 'computational' only when explicitly supported. If the method is "
            "unstated, retain the fact without inventing a method; it can be reviewed. "
            "Preserve direct/indirect gap assignments, experimental technique, "
            "temperature and computational method/functional in conditions when "
            "reported. Never merge optical and computed values merely because the "
            "material is the same. Preserve the reported value, unit and any "
            "approximation or bound. Do not convert wavelengths or absorption edges "
            "to energies, infer a Tauc intercept, estimate values from a plot, or "
            "interpret activation, emission or exciton binding energies as band gaps. "
            "For multiple materials, bind each value to its own material and method. "
            "Return no fact when no explicit scalar band-gap value is supported."
        ),
        retrieval_queries=(
            "material composition optical band gap energy eV Tauc direct indirect",
            "material electronic fundamental band gap eV calculation functional",
        ),
        examples=(
            {
                "evidence": "Sample A (TiO2) has an optical band gap of 3.20 eV from a Tauc plot.",
                "facts": [
                    {
                        "material_reported": "TiO2",
                        "property": "band gap",
                        "value": 3.20,
                        "unit": "eV",
                        "qualifier": None,
                        "conditions": {
                            "determination_method": "optical",
                            "technique": "Tauc plot",
                        },
                    }
                ],
            },
            {
                "evidence": "For ZnO, the PBE calculation gives a direct band gap of 0.75 eV.",
                "facts": [
                    {
                        "material_reported": "ZnO",
                        "property": "band gap",
                        "value": 0.75,
                        "unit": "eV",
                        "qualifier": None,
                        "conditions": {
                            "determination_method": "computational",
                            "functional": "PBE",
                            "gap_type": "direct",
                        },
                    }
                ],
            },
            {
                "evidence": "TiO2 shows an absorption edge at 390 nm; its conductivity activation energy is 0.18 eV.",
                "facts": [],
            },
        ),
        allowed_units=("eV",),
        required_conditions=("determination_method",),
        evidence_providers=("rule_text", "table", "figure", "equation"),
        processing_kwargs={"allow_missing_doi": True},
    )
