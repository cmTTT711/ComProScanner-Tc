"""Strict multiset scoring with explicit FP and FN records."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class StrictMetrics:
    gold_facts: int
    predicted_facts: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    false_positives: tuple[dict[str, Any], ...]
    false_negatives: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _key(item: dict[str, Any]) -> tuple:
    fact_value = item.get("fact_value") or {}
    return (
        str(item.get("document_id", item.get("paper_id", ""))).strip().casefold(),
        str(item.get("property", item.get("property_name", "tc"))).strip().casefold(),
        str(
            item.get(
                "material_identity_key",
                item.get("material_normalized", item.get("material", "")),
            )
        ).strip().casefold(),
        str(
            item.get("value", item.get("tc_value", fact_value.get("value", "")))
        ).strip(),
        str(item.get("unit", item.get("tc_unit", fact_value.get("unit", "")))).strip(),
        item.get("qualifier", fact_value.get("qualifier")),
    )


def score_exact_facts(
    gold: list[dict[str, Any]], predictions: list[dict[str, Any]]
) -> StrictMetrics:
    """Score exact normalized facts without semantic or unit-conversion matching."""

    strict_gold = [item for item in gold if item.get("strict_scoring", True)]
    gold_by_key = {_key(item): item for item in strict_gold}
    predictions_by_key = {_key(item): item for item in predictions}
    gold_counts = Counter(map(_key, strict_gold))
    prediction_counts = Counter(map(_key, predictions))
    tp = sum((gold_counts & prediction_counts).values())
    fp_counter = prediction_counts - gold_counts
    fn_counter = gold_counts - prediction_counts
    fp = sum(fp_counter.values())
    fn = sum(fn_counter.values())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_positives = tuple(
        predictions_by_key[key] for key, count in fp_counter.items() for _ in range(count)
    )
    false_negatives = tuple(
        gold_by_key[key] for key, count in fn_counter.items() for _ in range(count)
    )
    return StrictMetrics(
        gold_facts=len(strict_gold),
        predicted_facts=len(predictions),
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )
