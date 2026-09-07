import pytest

from comproscanner.documents.docling import matches_property_keywords
from comproscanner.presets.curie_temperature import PROPERTY_KEYWORDS


KEYWORDS = PROPERTY_KEYWORDS


@pytest.mark.parametrize("text", [
    "TC = 774 K", "TC≈774 K", "TC ∼ 774 K", "TC�774 K",
    "T_C = 774 K", "T C = 774 K", "Curie temperature is 450 K",
    "Curie point of 450 K", "ferroelectric-paraelectric transition at 150 °C",
    "ferroelectric to paraelectric transition near 125 °C",
    "a maximum at 150 °C was assigned to the ferroelectric-paraelectric transition",
    "normal ferroelectric transition at 732 K",
    "ferroelectric transition temperature Tm = 320 °C",
    "Tm = 320 °C; the local discussion identifies a ferroelectric to paraelectric transition.",
])
def test_tc_candidate_signals_pass(text):
    assert matches_property_keywords(text, KEYWORDS)


@pytest.mark.parametrize("text", [
    "sintered at 1250 °C", "annealed at 700 °C", "calcined at 850 °C",
    "measured at 300 K", "heated to 500 °C", "room temperature 300 K",
    "measurement temperature was 10 K", "aging temperature was 120 °C",
    "DOI: 10.1039/c6tc00995f",
])
def test_generic_temperatures_reject(text):
    assert not matches_property_keywords(text, KEYWORDS)
