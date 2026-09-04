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


def test_typographic_material_variants_merge_and_remain_auditable():
    first = make_fact(evidence="text_1")
    parenthetical = Fact(
        document_id="paper_001",
        property_name="Tc",
        material_reported="BiFeO3 (BFO)",
        material_normalized="BiFeO3 (BFO)",
        material_identity_key="BiFeO3 (BFO)",
        fact_value=FactValue.from_raw(1103, "K"),
        evidence_ids=("text_2",),
    )
    merged = merge_facts([first, parenthetical])
    assert len(merged) == 1
    assert merged[0].evidence_ids == ("text_1", "text_2")
    assert merged[0].material_reported_variants == ("BiFeO3", "BiFeO3 (BFO)")


def test_pdf_spacing_and_decimal_ocr_variants_merge():
    first = Fact(
        "paper_015",
        "Tc",
        "0.74BiFeO3 - 0.26(Ba0.85Ca0.15)TiO3",
        "0.74BiFeO3 - 0.26(Ba0.85Ca0.15)TiO3",
        "0.74BiFeO3 - 0.26(Ba0.85Ca0.15)TiO3",
        FactValue.from_raw(698, "K"),
        ("text_1",),
    )
    second = Fact(
        "paper_015",
        "Tc",
        "0.74BiFeO3-0.26(Ba0:85Ca0:15)TiO3",
        "0.74BiFeO3-0.26(Ba0:85Ca0:15)TiO3",
        "0.74BiFeO3-0.26(Ba0:85Ca0:15)TiO3",
        FactValue.from_raw(698, "K"),
        ("text_2",),
    )
    assert len(merge_facts([first, second])) == 1


def test_material_state_and_composition_are_never_erased_for_merging():
    bulk = make_fact()
    film = Fact(
        "paper_001",
        "Tc",
        "BiFeO3 thin film",
        "BiFeO3 thin film",
        "BiFeO3 thin film",
        FactValue.from_raw(1103, "K"),
        ("text_2",),
    )
    doped = Fact(
        "paper_001",
        "Tc",
        "La-doped BiFeO3",
        "La-doped BiFeO3",
        "La-doped BiFeO3",
        FactValue.from_raw(1103, "K"),
        ("text_3",),
    )
    assert len(merge_facts([bulk, film, doped])) == 3
