"""Main commands for the canonical workflow."""

from __future__ import annotations

import argparse
import json
from comproscanner.presets import get_preset
from comproscanner.presets import list_presets
from comproscanner.documents.ingestion import default_source_registry
from comproscanner.documents.ingestion import normalize_article_csvs
from comproscanner.documents.literature import CorpusLayout
from .run import _RUN_STAGES
from .documents import _acquire_oa
from .documents import _discover
from .results import _evaluate
from .extraction import _extract_evidence
from .results import _postprocess_materials
from .evidence import _prepare_evidence
from .documents import _process_articles
from .results import _review
from .run import _run_pipeline


def _add_model_arguments(parser: argparse.ArgumentParser) -> None:
    """One runtime configuration shared by every property and CLI entry point."""
    parser.add_argument("--identifier-model", default=None)
    parser.add_argument("--identifier-base-url", default=None)
    parser.add_argument("--identifier-api-key-env", default=None)
    parser.add_argument("--extractor-model", default=None)
    parser.add_argument("--extractor-base-url")
    parser.add_argument("--extractor-api-key-env")
    parser.add_argument(
        "--vision-model", help="Required when prepared Evidence contains figures"
    )
    parser.add_argument("--vision-base-url")
    parser.add_argument("--vision-api-key-env")
    parser.add_argument("--timeout", type=int, default=180)


def _apply_preset_defaults(args):
    if not getattr(args, "preset", None):
        return
    preset = get_preset(args.preset)
    if hasattr(args, "rag_top_k") and args.rag_top_k is None:
        args.rag_top_k = preset.rag_settings.get("rag_top_k", 3)
    for role, settings in preset.models.items():
        for field in ("model", "base_url", "api_key_env"):
            name = f"{role}_{field}"
            if getattr(args, name, None) is None:
                setattr(args, name, settings.get(field))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="comproscanner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("presets", help="List registered property presets")
    subparsers.add_parser("sources", help="List registered article-source adapters")
    corpus = subparsers.add_parser(
        "init-corpus", help="Create separated manual/downloaded/normalized PDF folders"
    )
    corpus.add_argument("--root", default="data/literature/pdfs")
    discover = subparsers.add_parser(
        "discover", help="Search Scopus metadata; requires explicit network execution"
    )
    discover.add_argument("--query", required=True)
    discover.add_argument("--start-year", type=int, required=True)
    discover.add_argument("--end-year", type=int, required=True)
    discover.add_argument("--limit", type=int, default=500)
    discover.add_argument("--shortlist", type=int, default=200)
    discover.add_argument("--delay", type=float, default=1.0)
    discover.add_argument("--open-access-only", action="store_true")
    discover.add_argument("--exclude-csv", action="append", default=[])
    discover.add_argument("--api-key-env", default="SCOPUS_API_KEY")
    discover.add_argument("--output", default="data/literature/acquisition/discovery")
    discover.add_argument("--execute-network", action="store_true")
    acquire = subparsers.add_parser(
        "acquire-oa", help="Resolve and download validated OA PDFs"
    )
    acquire.add_argument("--shortlist", required=True)
    acquire.add_argument("--corpus-root", default="data/literature/pdfs")
    acquire.add_argument("--output", default="data/literature/acquisition/downloads")
    acquire.add_argument(
        "--semantic-scholar-api-key-env", default="SEMANTIC_SCHOLAR_API_KEY"
    )
    acquire.add_argument("--execute-network", action="store_true")
    normalize = subparsers.add_parser(
        "normalize", help="Merge processor CSV files into one canonical Article CSV"
    )
    normalize.add_argument("--csv", action="append", required=True)
    normalize.add_argument("--output", required=True)
    normalize.add_argument("--source-type", default="mixed")
    process = subparsers.add_parser(
        "process-articles",
        help="Plan or explicitly run the registered PDF/publisher processors",
    )
    process.add_argument("--source", action="append", required=True)
    process.add_argument("--preset", default="curie_temperature")
    process.add_argument("--folder")
    process.add_argument(
        "--workspace",
        help="Parser artifacts directory; default data/literature/processing/<preset>",
    )
    process.add_argument(
        "--doi-file", help="UTF-8 text file containing one DOI per line"
    )
    process.add_argument("--save-xml", action="store_true")
    process.add_argument("--save-pdf", action="store_true")
    process.add_argument("--execute-processing", action="store_true")
    process.add_argument("--execute-network", action="store_true")
    prepare = subparsers.add_parser(
        "prepare-evidence",
        help="Create canonical chunks and Evidence without external LLM calls",
    )
    prepare.add_argument("--csv", required=True)
    prepare.add_argument("--preset", default="curie_temperature")
    prepare.add_argument("--outputs", default="data")
    prepare.add_argument("--run-id")
    prepare.add_argument("--source-type", default="unknown")
    prepare.add_argument("--target-words", type=int, default=220)
    prepare.add_argument("--max-words", type=int, default=360)
    prepare.add_argument("--overlap-words", type=int, default=60)
    prepare.add_argument("--with-rag", action="store_true")
    prepare.add_argument(
        "--provider",
        action="append",
        choices=("rule_text", "physbert", "table", "figure", "equation"),
        help="Override preset Evidence providers; repeat for multiple providers",
    )
    prepare.add_argument("--rag-top-k", type=int, default=None)
    prepare.add_argument("--resume", action="store_true")
    extract = subparsers.add_parser(
        "extract", help="Run Qwen and DeepSeek over prepared Evidence"
    )
    extract.add_argument("--run-id", required=True)
    extract.add_argument("--preset", default="curie_temperature")
    extract.add_argument("--outputs", default="data")
    _add_model_arguments(extract)
    extract.add_argument("--execute", action="store_true")
    extract.add_argument("--force", action="store_true")
    extract.add_argument("--resume", action="store_true")
    extract.add_argument(
        "--material-normalizer",
        choices=("article", "identity", "material-parser-api"),
        default="article",
    )
    extract.add_argument(
        "--article-csv",
        help="Same-Article material definitions; defaults to prepared Article input",
    )
    extract.add_argument("--execute-network", action="store_true")
    review = subparsers.add_parser(
        "review", help="Create a one-Fact-per-row workbook with original Evidence"
    )
    review.add_argument("--run-id", required=True)
    review.add_argument("--outputs", default="data")
    accept = subparsers.add_parser(
        "accept-review", help="Create new Gold from ACCEPT/MODIFY Review rows"
    )
    accept.add_argument("--review", required=True)
    accept.add_argument("--output", required=True)
    evaluate = subparsers.add_parser(
        "evaluate", help="Calculate strict TP/FP/FN metrics"
    )
    evaluate.add_argument("--run-id", required=True)
    evaluate.add_argument("--gold", required=True)
    evaluate.add_argument("--preset", help="Defaults to the run preset")
    evaluate.add_argument(
        "--paper-map", help="JSON mapping of Gold paper_id to document_id"
    )
    evaluate.add_argument("--outputs", default="data")
    run = subparsers.add_parser(
        "run", help="Plan or execute the canonical Article-to-evaluation workflow"
    )
    inputs = run.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--csv", help="Existing canonical or legacy Article CSV")
    inputs.add_argument(
        "--processor-csv",
        action="append",
        default=[],
        help="Processor CSV to normalize first; repeat for multiple files",
    )
    inputs.add_argument(
        "--source",
        action="append",
        help="Raw registered article source to process first; repeat for multiple sources",
    )
    run.add_argument("--folder", help="PDF folder for manual_pdf/downloaded_pdf")
    run.add_argument("--doi-file", help="UTF-8 file containing one DOI per line")
    run.add_argument("--save-xml", action="store_true")
    run.add_argument("--save-pdf", action="store_true")
    run.add_argument("--preset", default="curie_temperature")
    run.add_argument("--run-id")
    run.add_argument("--outputs", default="data")
    run.add_argument("--source-type", default="mixed")
    run.add_argument("--through", choices=_RUN_STAGES, default="review")
    run.add_argument("--gold")
    run.add_argument("--paper-map")
    run.add_argument(
        "--provider",
        action="append",
        choices=("rule_text", "physbert", "table", "figure", "equation"),
    )
    run.add_argument("--with-rag", action="store_true")
    run.add_argument("--rag-top-k", type=int, default=None)
    run.add_argument("--target-words", type=int, default=220)
    run.add_argument("--max-words", type=int, default=360)
    run.add_argument("--overlap-words", type=int, default=60)
    _add_model_arguments(run)
    run.add_argument(
        "--material-normalizer",
        choices=("article", "identity", "material-parser-api"),
        default="article",
    )
    run.add_argument("--execute-pipeline", action="store_true")
    run.add_argument("--execute-models", action="store_true")
    run.add_argument("--execute-network", action="store_true")
    run.add_argument("--force", action="store_true")
    run.add_argument("--resume", action="store_true")
    postprocess = subparsers.add_parser(
        "postprocess-materials",
        help="Apply material tools to saved facts without any model calls",
    )
    postprocess.add_argument("--predictions", required=True)
    postprocess.add_argument("--evidence", required=True)
    postprocess.add_argument("--article-csv", required=True)
    postprocess.add_argument("--run-id", required=True)
    postprocess.add_argument("--outputs", default="data")
    postprocess.add_argument("--preset", default="curie_temperature")
    postprocess.add_argument(
        "--material-normalizer", choices=("article", "identity"), default="article"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _apply_preset_defaults(args)
    if args.command == "presets":
        print("\n".join(list_presets()))
        return 0
    if args.command == "sources":
        for source in default_source_registry().list():
            credentials = ",".join(source.credential_env) or "-"
            optional_credentials = ",".join(source.optional_credential_env) or "-"
            print(
                f"{source.name}\t{source.raw_format}\t{source.processor}\t"
                f"network={str(source.network_required).lower()}\t"
                f"credentials={credentials}\toptional_credentials={optional_credentials}"
            )
        return 0
    if args.command == "init-corpus":
        layout = CorpusLayout.from_root(args.root)
        layout.initialize()
        print(json.dumps(layout.as_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "discover":
        if args.shortlist < 1 or args.shortlist > args.limit:
            raise ValueError("Require 1 <= shortlist <= limit")
        return _discover(args)
    if args.command == "acquire-oa":
        return _acquire_oa(args)
    if args.command == "normalize":
        print(
            normalize_article_csvs(args.csv, args.output, source_type=args.source_type)
        )
        return 0
    if args.command == "process-articles":
        return _process_articles(args)
    if args.command == "prepare-evidence":
        return _prepare_evidence(args)
    if args.command == "extract":
        return _extract_evidence(args)
    if args.command == "review":
        return _review(args)
    if args.command == "postprocess-materials":
        return _postprocess_materials(args)
    if args.command == "accept-review":
        from comproscanner.results.gold import accept_review

        print(accept_review(args.review, args.output))
        return 0
    if args.command == "evaluate":
        return _evaluate(args)
    if args.command == "run":
        return _run_pipeline(args)
    raise AssertionError(f"Unhandled command: {args.command}")
