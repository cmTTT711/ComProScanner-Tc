"""Focused checks for the production Tc configuration retained after recovery."""

def test_tc_recovery_configuration():
    from comproscanner.cli.main import build_parser
    from comproscanner.presets import get_preset

    preset = get_preset("curie_temperature")
    keywords = preset.property_keywords

    def matches(text):
        from comproscanner.utils.pdf_to_markdown_text import matches_property_keywords

        return matches_property_keywords(text, keywords)

    assert preset.processing_kwargs["allow_missing_doi"] is True
    assert matches(
        "The ferroelectric transition temperature shifts with composition."
    )
    assert matches(
        "The ferroelectric to paraelectric phase transition temperature, Tc decreases."
    )
    assert not matches("The sample was measured at a temperature of 300 K.")
    extract_args = build_parser().parse_args(["extract", "--run-id", "check"])
    assert extract_args.timeout == 180


def test_tc_schema_and_scientific_prompt_remain_unchanged():
    from comproscanner.presets.curie_temperature import (
        get_curie_temperature_flow_optional_args,
    )

    args = get_curie_temperature_flow_optional_args()
    example = args["expected_composition_property_example"]
    notes = " ".join(
        args["composition_property_extraction_agent_notes"]
        + args["composition_property_extraction_task_notes"]
    )

    assert '"compositions"' in example
    assert '"property_unit"' in example
    assert '"family"' in example
    assert "Néel temperatures" in notes
    assert "background or comparison materials" in notes
    assert "do not invent one" in notes
