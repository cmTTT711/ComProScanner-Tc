"""Strict multiset scoring with explicit FP and FN records."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
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
    property_name = item.get("property", item.get("property_name"))
    if not isinstance(property_name, str) or not property_name.strip():
        raise ValueError("Each scored fact must declare property or property_name")
    fact_value = item.get("fact_value") or {}
    if not isinstance(fact_value, dict):
        raise ValueError("fact_value must be an object containing value and unit")
    value = item.get("value", fact_value.get("value"))
    unit = item.get("unit", fact_value.get("unit"))
    if value is None or not str(value).strip() or unit is None:
        raise ValueError(
            "Each scored fact must declare value and unit, directly or in fact_value"
        )
    conditions = item.get("conditions")
    if conditions is None:
        conditions = {}
    if not isinstance(conditions, dict):
        raise ValueError("Fact conditions must be an object")
    try:
        conditions_key = json.dumps(
            conditions,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Fact conditions must contain JSON-compatible values") from exc
    return (
        str(item.get("document_id", item.get("paper_id", ""))).strip().casefold(),
        property_name.strip().casefold(),
        str(
            item.get(
                "material_identity_key",
                item.get("material_normalized", item.get("material", "")),
            )
        )
        .strip()
        .casefold(),
        str(value).strip(),
        str(unit).strip(),
        item.get("qualifier", fact_value.get("qualifier")),
        conditions_key,
        json.dumps(
            item.get("attributes") or {},
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        ),
    )


def score_exact_facts(
    gold: list[dict[str, Any]], predictions: list[dict[str, Any]]
) -> StrictMetrics:
    """Score exact facts, including conditions, without semantic or unit conversion.

    Property, value and unit must be explicit. Legacy property-specific records
    must be converted at their import boundary before calling this scorer.
    Missing conditions mean an empty object, not a wildcard.
    """

    strict_gold = [item for item in gold if item.get("strict_scoring", True)]
    gold_pairs = [(_key(item), item) for item in strict_gold]
    prediction_pairs = [(_key(item), item) for item in predictions]
    gold_by_key = dict(gold_pairs)
    predictions_by_key = dict(prediction_pairs)
    gold_counts = Counter(key for key, _ in gold_pairs)
    prediction_counts = Counter(key for key, _ in prediction_pairs)
    tp = sum((gold_counts & prediction_counts).values())
    fp_counter = prediction_counts - gold_counts
    fn_counter = gold_counts - prediction_counts
    fp = sum(fp_counter.values())
    fn = sum(fn_counter.values())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_positives = tuple(
        predictions_by_key[key]
        for key, count in fp_counter.items()
        for _ in range(count)
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
