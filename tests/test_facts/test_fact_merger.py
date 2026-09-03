from comproscanner.facts import Fact, FactValue, merge_facts


def make_fact(unit="K", value=1103, qualifier=None, evidence="text_1"):
    return Fact(
        document_id="paper_001",
        property_name="Tc",
        material_reported="BiFeO3",
        material_normalized="BiFeO3",
        material_identity_key="BiFeO3",
        fact_value=FactValue.from_raw(value, unit, qualifier),
        evidence_ids=(evidence,),
    )


def test_exact_facts_merge_and_keep_all_evidence():
    merged = merge_facts([make_fact(), make_fact(evidence="table_1")])
    assert len(merged) == 1
    assert merged[0].evidence_ids == ("text_1", "table_1")


def test_units_are_not_implicitly_converted_or_merged():
    assert len(merge_facts([make_fact("K", 1103), make_fact("°C", 830)])) == 2


def test_qualifiers_are_not_discarded_during_merge():
    facts = [make_fact(value=580), make_fact(value=580, qualifier="above")]
    assert len(merge_facts(facts)) == 2
