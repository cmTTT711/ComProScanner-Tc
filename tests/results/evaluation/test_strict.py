import pytest

from comproscanner.presets import get_preset
from comproscanner.results.evaluation import score_exact_facts
from comproscanner.results.evaluation.inputs import adapt_records


def fact(material, value, strict=True):
    return {
        "paper_id": 1,
        "property": "Tc",
        "material": material,
        "value": value,
        "unit": "K",
        "strict_scoring": strict,
    }


def test_strict_metrics_report_fp_fn_precision_recall_and_f1():
    metrics = score_exact_facts(
        [fact("A", 100), fact("B", 200), fact("range", 300, strict=False)],
        [fact("A", 100), fact("C", 400)],
    )
    assert (metrics.tp, metrics.fp, metrics.fn) == (1, 1, 1)
    assert metrics.precision == metrics.recall == metrics.f1 == 0.5
    assert metrics.false_positives[0]["material"] == "C"
    assert metrics.false_negatives[0]["material"] == "B"


def test_new_nested_fact_value_shape_is_supported():
    gold = [fact("A", 100)]
    prediction = [
        {
            "document_id": "1",
            "property_name": "Tc",
            "material_identity_key": "A",
            "fact_value": {"value": "100", "unit": "K", "qualifier": None},
        }
    ]
    metrics = score_exact_facts(gold, prediction)
    assert (metrics.tp, metrics.fp, metrics.fn) == (1, 0, 0)


def test_non_tc_property_uses_same_scorer_and_is_part_of_identity():
    gold = [{**fact("ZnO", "3.3"), "property": "band_gap", "unit": "eV"}]
    prediction = [
        {
            "document_id": "1",
            "property_name": "band_gap",
            "material_normalized": "ZnO",
            "fact_value": {"value": "3.3", "unit": "eV"},
        }
    ]
    assert score_exact_facts(gold, prediction).tp == 1
    prediction[0]["property_name"] = "activation_energy"
    metrics = score_exact_facts(gold, prediction)
    assert (metrics.tp, metrics.fp, metrics.fn) == (0, 1, 1)


@pytest.mark.parametrize("property_name", [None, "", "   "])
@pytest.mark.parametrize("side", ["gold", "predictions"])
def test_missing_property_is_an_error_on_either_side(property_name, side):
    invalid = fact("A", 100)
    if property_name is None:
        del invalid["property"]
    else:
        invalid["property"] = property_name
    records = {"gold": [fact("A", 100)], "predictions": [fact("A", 100)]}
    records[side] = [invalid]
    with pytest.raises(ValueError, match="property or property_name"):
        score_exact_facts(**records)


@pytest.mark.parametrize("field", ["value", "unit"])
def test_missing_generic_value_or_unit_is_an_error(field):
    invalid = fact("A", 100)
    del invalid[field]
    with pytest.raises(ValueError, match="value and unit"):
        score_exact_facts([invalid], [])


def test_legacy_tc_records_require_explicit_import_conversion():
    legacy = {
        "paper_id": 1,
        "material": "A",
        "tc_value": 100,
        "tc_unit": "K",
        "conditions": {"structure": "trilayer"},
        "review_note": "accepted",
    }
    with pytest.raises(ValueError, match="property or property_name"):
        score_exact_facts([legacy], [])
    with pytest.raises(ValueError, match="value and unit"):
        score_exact_facts([{**legacy, "property": "Tc"}], [])
    preset = get_preset("curie_temperature")
    gold = adapt_records([legacy], preset)
    prediction = adapt_records(
        [{**fact("A", 100), "conditions": {"structure": "trilayer"}}], preset
    )
    assert score_exact_facts(gold, prediction).tp == 1
    assert gold[0]["review_note"] == "accepted"
    assert "tc_value" not in gold[0]
    assert "property" not in legacy  # Reading a historical gold does not rewrite it.


def test_legacy_adapter_does_not_guess_property_for_generic_records():
    generic = {"material": "A", "value": 100, "unit": "K"}
    converted = adapt_records([generic], get_preset("curie_temperature"))
    assert converted == [generic]
    with pytest.raises(ValueError, match="property or property_name"):
        score_exact_facts(converted, [])


def test_legacy_adapter_rejects_conflicting_property_and_values():
    preset = get_preset("curie_temperature")
    with pytest.raises(ValueError, match="conflict with the selected property preset"):
        adapt_records(
            [{"property": "band_gap", "tc_value": 3.3, "tc_unit": "eV"}], preset
        )
    with pytest.raises(ValueError, match="Conflicting tc_value and value"):
        adapt_records([{"tc_value": 100, "value": 200, "tc_unit": "K"}], preset)


def test_conditions_distinguish_experiments_and_missing_is_not_a_wildcard():
    gold = [{**fact("A", 100), "conditions": {"structure": "trilayer"}}]
    prediction = [{**fact("A", 100), "conditions": {"structure": "randomly mixed"}}]
    metrics = score_exact_facts(gold, prediction)
    assert (metrics.tp, metrics.fp, metrics.fn) == (0, 1, 1)
    assert metrics.false_positives[0]["conditions"]["structure"] == "randomly mixed"
    assert score_exact_facts(gold, [fact("A", 100)]).tp == 0


def test_condition_key_order_does_not_change_identity():
    gold = [
        {
            **fact("A", 100),
            "conditions": {
                "method": "optical",
                "temperature": {"value": 300, "unit": "K"},
            },
        }
    ]
    prediction = [
        {
            **fact("A", 100),
            "conditions": {
                "temperature": {"unit": "K", "value": 300},
                "method": "optical",
            },
        }
    ]
    assert score_exact_facts(gold, prediction).tp == 1
    assert (
        score_exact_facts([fact("A", 100)], [{**fact("A", 100), "conditions": {}}]).tp
        == 1
    )


def test_strict_scoring_preserves_multiset_counts():
    metrics = score_exact_facts(
        [fact("A", 100), fact("A", 100), fact("B", 200)],
        [fact("A", 100), fact("B", 200), fact("B", 200)],
    )
    assert (metrics.tp, metrics.fp, metrics.fn) == (2, 1, 1)
    assert metrics.false_positives == (fact("B", 200),)
    assert metrics.false_negatives == (fact("A", 100),)


def test_units_and_qualifiers_still_match_exactly():
    gold = [fact("A", 100)]
    for prediction in (
        {**fact("A", 100), "unit": "k"},
        {**fact("A", 100), "qualifier": "approximately"},
        {**fact("A", "100.0")},
    ):
        assert score_exact_facts(gold, [prediction]).tp == 0


@pytest.mark.parametrize("conditions", [[], "annealed", {"pressure": float("nan")}])
def test_invalid_conditions_are_rejected_instead_of_matching(conditions):
    with pytest.raises(ValueError, match="conditions"):
        score_exact_facts([{**fact("A", 100), "conditions": conditions}], [])


def test_explicit_empty_unit_is_valid_for_dimensionless_properties():
    gold = [{**fact("A", 100), "property": "relative_permittivity", "unit": ""}]
    assert score_exact_facts(gold, gold).tp == 1


def test_excluded_gold_does_not_require_a_scoreable_fact():
    metrics = score_exact_facts([{"strict_scoring": False, "review_note": "range"}], [])
    assert metrics.gold_facts == 0
