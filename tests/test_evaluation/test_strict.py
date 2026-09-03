from comproscanner.evaluation import score_exact_facts


def fact(material, value, strict=True):
    return {
        "paper_id": 1,
        "property": "Tc",
        "material": material,
        "tc_value": value,
        "tc_unit": "K",
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
    prediction = [{
        "document_id": "1",
        "property_name": "Tc",
        "material_identity_key": "A",
        "fact_value": {"value": "100", "unit": "K", "qualifier": None},
    }]
    metrics = score_exact_facts(gold, prediction)
    assert (metrics.tp, metrics.fp, metrics.fn) == (1, 0, 0)
