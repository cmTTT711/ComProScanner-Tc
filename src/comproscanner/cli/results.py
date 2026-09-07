"""Results commands for the canonical workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from comproscanner._paths import resolve_recorded_path
from comproscanner.presets import get_preset
from comproscanner.results import RunStore
from comproscanner.results import write_review_workbook
from comproscanner.results.facts import FactProcessor
from comproscanner.results.facts import ArticleMaterialNormalizer
from comproscanner.results.facts import MaterialParserAPINormalizer
from comproscanner.results.facts import merge_facts
from comproscanner.results.evaluation.inputs import adapt_records
from comproscanner.results.evaluation import score_exact_facts
from comproscanner.documents.schemas import normalize_legacy_article_frame
from comproscanner.documents.csv_store import read_csv_sanitizing_nul
from .common import _fact_from_dict
from .common import _load_evidence


def _material_article_config(args, store):
    explicit = getattr(args, "article_csv", None)
    prepared = (
        store.read_json("run_config.json", {}).get("preparation", {}).get("source_csv")
    )
    path = resolve_recorded_path(explicit or prepared or store.run_dir / "article.csv")
    if explicit and not path.is_file():
        raise FileNotFoundError(path)
    return (
        {
            "path": str(path.resolve()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        if path.is_file()
        else None
    )


def _material_processor(args, store, evidence, abbreviations=None):
    preset = get_preset(args.preset)
    normalizer = None
    if args.material_normalizer == "article":
        contexts = {}
        sources = {}
        article = _material_article_config(args, store)
        if article:
            frame = normalize_legacy_article_frame(
                read_csv_sanitizing_nul(article["path"])
            )
            for _, row in frame.fillna("").iterrows():
                document_id = str(row["document_id"])
                contexts[document_id] = str(
                    row["full_text"]
                    or "\n".join(
                        str(row.get(key, ""))
                        for key in (
                            "abstract",
                            "introduction",
                            "exp_methods",
                            "results_discussion",
                            "conclusion",
                        )
                    )
                )
                sources[document_id] = article
                pdf = resolve_recorded_path(str(row.get("source_path", "")))
                if pdf.suffix.casefold() == ".pdf" and pdf.is_file():
                    # Use the same Article's local PDF for material definitions;
                    # legacy CSV text can lose minus signs and formula digits.
                    import pymupdf

                    try:
                        with pymupdf.open(pdf) as document:
                            text = "\n".join(page.get_text() for page in document)
                        if text.strip():
                            contexts[document_id] = text
                            sources[document_id] = {
                                "path": str(row.get("source_path", pdf.resolve())),
                                "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                                "reader": "pymupdf",
                            }
                    except (RuntimeError, ValueError):
                        pass  # Article text remains available; unresolved names are flagged.
        for item in evidence:
            if item.document_id not in contexts:
                contexts[item.document_id] = "\n".join(
                    e.content for e in evidence if e.document_id == item.document_id
                )
        normalizer = ArticleMaterialNormalizer(contexts, abbreviations, sources)
    elif args.material_normalizer == "material-parser-api":
        normalizer = MaterialParserAPINormalizer()
    return FactProcessor(
        normalizer,
        allowed_units=preset.allowed_units,
        required_conditions=preset.required_conditions,
    )


def _postprocess_materials(args):
    """Replay saved extraction through the same material tools, with no models."""
    store = RunStore(args.outputs, args.run_id)
    if store.run_dir.exists() and any(store.run_dir.iterdir()):
        raise FileExistsError("Use an empty new run-id to preserve existing results")
    source = Path(args.predictions).resolve()
    facts = [
        _fact_from_dict(item) for item in json.loads(source.read_text(encoding="utf-8"))
    ]
    evidence = _load_evidence(Path(args.evidence))
    processor = _material_processor(args, store, evidence)
    processed = [processor.process(fact) for fact in facts]
    merged = merge_facts(processed)
    store.initialize()
    store.write_json("evidence/all.json", [item.to_dict() for item in evidence])
    store.write_json("predictions.json", [fact.to_dict() for fact in merged])
    store.write_json(
        "material_changes.json",
        [
            {"source_row": index, "before": before.to_dict(), "after": after.to_dict()}
            for index, (before, after) in enumerate(
                zip(facts, processed, strict=True), 1
            )
        ],
    )
    store.write_json(
        "run_config.json",
        {
            "preset": args.preset,
            "source_predictions": str(source),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "material_article": _material_article_config(args, store),
            "material_normalizer": args.material_normalizer,
            "external_calls": 0,
        },
    )
    store.write_json(
        "summary.json",
        {
            "facts_before": len(facts),
            "facts_after_merge": len(merged),
            "materials_changed": sum(
                a.material_normalized != b.material_normalized
                for a, b in zip(facts, processed)
            ),
            "facts_needing_review": sum(bool(f.processing_issues) for f in processed),
            "external_calls": 0,
            "extraction_replayed": False,
        },
    )
    write_review_workbook(store.run_dir / "review.xlsx", merged, evidence)
    _export_results(store, merged, args.article_csv)
    print(store.run_dir)
    return 0


def _export_results(store, facts, article_path=None):
    from comproscanner.results.export import write_results_workbook

    config = store.read_json("run_config.json", {})
    source = article_path or (config.get("material_article") or {}).get("path")
    source = (
        source
        or config.get("preparation", {}).get("source_csv")
        or store.run_dir / "article.csv"
    )
    source = resolve_recorded_path(source)
    frame = read_csv_sanitizing_nul(source) if source.is_file() else None
    write_results_workbook(store.run_dir / "predictions.xlsx", facts, frame)


def _review(args: argparse.Namespace) -> int:
    store = RunStore(args.outputs, args.run_id)
    predictions_path = store.run_dir / "predictions.json"
    evidence_path = store.run_dir / "evidence" / "all.json"
    facts = [
        _fact_from_dict(item)
        for item in json.loads(predictions_path.read_text(encoding="utf-8"))
    ]
    evidence = _load_evidence(evidence_path)
    destination = store.run_dir / "review.xlsx"
    write_review_workbook(destination, facts, evidence)
    _export_results(store, facts)
    print(destination)
    return 0


def _evaluate(args: argparse.Namespace) -> int:
    store = RunStore(args.outputs, args.run_id)
    config = store.read_json("run_config.json", {})
    preset = get_preset(
        getattr(args, "preset", None) or config.get("preset") or "curie_temperature"
    )
    map_path = getattr(args, "paper_map", None)
    paper_map = (
        json.loads(Path(map_path).read_text(encoding="utf-8")) if map_path else None
    )
    gold = adapt_records(
        json.loads(Path(args.gold).read_text(encoding="utf-8")), preset, paper_map
    )
    predictions = json.loads(
        (store.run_dir / "predictions.json").read_text(encoding="utf-8")
    )
    predictions = adapt_records(predictions, preset, paper_map)
    scored_gold = [item for item in gold if item.get("strict_scoring", True)]
    if scored_gold and predictions:
        gold_ids = {
            str(item.get("document_id", item.get("paper_id", ""))).strip().casefold()
            for item in scored_gold
        }
        prediction_ids = {
            str(item.get("document_id", item.get("paper_id", ""))).strip().casefold()
            for item in predictions
        }
        if not gold_ids & prediction_ids:
            raise ValueError(
                "Gold and prediction document IDs do not overlap; align paper_id/DOI before evaluation"
            )
        gold_properties = {
            str(item.get("property", item.get("property_name", ""))).strip().casefold()
            for item in scored_gold
        }
        prediction_properties = {
            str(item.get("property", item.get("property_name", ""))).strip().casefold()
            for item in predictions
        }
        if not gold_properties & prediction_properties:
            raise ValueError(
                "Gold and prediction property names do not overlap; align names before evaluation"
            )
    metrics = score_exact_facts(gold, predictions)
    destination = store.write_json("metrics.json", metrics.to_dict())
    print(destination)
    return 0
