"""Unified CLI; evidence preparation is local and never calls an external LLM."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path

from ..chunking import TextChunkConfig
from ..agents import EvidenceAgentFlow
from ..evidence import Evidence, EvidenceType, RetrievalMethod
from ..evidence.providers import VectorTextEvidenceProvider
from ..evidence.vector_store import CanonicalChunkVectorStore
from ..pipeline import EvidencePreparationPipeline
from ..presets import get_preset, list_presets
from ..results import RunStore, write_review_workbook
from ..facts import (
    Fact,
    FactProcessor,
    FactValue,
    MaterialParserAPINormalizer,
    merge_facts,
)
from ..evaluation import score_exact_facts
from ..schemas import normalize_legacy_article_frame, validate_article_frame
from ..ingestion import (
    build_processing_plan,
    default_source_registry,
    execute_processing_plan,
    format_processing_plan,
    normalize_article_csvs,
    read_doi_file,
)
from ..literature import (
    CorpusLayout,
    DownloadSource,
    ScopusSearch,
    atomic_csv,
    atomic_json,
    discover_scopus,
    download_validated_pdf,
    existing_pdf_hashes,
    normalize_doi,
    read_csv,
    resolve_openalex_urls,
    resolve_semantic_scholar,
    safe_filename,
)
from ..utils.configs import RAGConfig
from ..utils.data_preparator import read_csv_sanitizing_nul


def _default_run_id(preset: str) -> str:
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{preset}"


def _safe_file_stem(value: str) -> str:
    """Return a deterministic Windows-safe name without changing the document id."""
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if char in invalid or ord(char) < 32 else char for char in value)
    return cleaned.strip(" .") or "document"


def _require_network_execution(args: argparse.Namespace) -> None:
    if not args.execute_network:
        raise SystemExit(
            "Network access is disabled. Re-run with --execute-network only after "
            "explicit approval."
        )


def _discover(args: argparse.Namespace) -> int:
    _require_network_execution(args)
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing API key environment variable: {args.api_key_env}")
    excluded = set()
    for path in args.exclude_csv:
        excluded.update(normalize_doi(row.get("doi")) for row in read_csv(path))
    search = ScopusSearch(
        query=args.query,
        start_year=args.start_year,
        end_year=args.end_year,
        limit=args.limit,
        open_access_only=args.open_access_only,
        delay_seconds=args.delay,
    )
    rows = discover_scopus(search, api_key, excluded_dois=excluded)
    rows.sort(
        key=lambda row: (
            -int(row.get("cited_by_count") or 0),
            -int(row.get("year") or 0),
            row.get("title", "").casefold(),
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["candidate_rank"] = rank
    output = Path(args.output).resolve()
    atomic_csv(output / "candidates.csv", rows)
    atomic_json(output / "candidates.json", rows)
    atomic_csv(output / "shortlist.csv", rows[: args.shortlist])
    atomic_json(
        output / "summary.json",
        {
            "source": "scopus",
            "query": args.query,
            "year_range": [args.start_year, args.end_year],
            "candidate_count": len(rows),
            "shortlist_count": min(len(rows), args.shortlist),
            "full_text_downloaded": False,
            "llm_called": False,
        },
    )
    print(output)
    return 0


def _acquire_oa(args: argparse.Namespace) -> int:
    _require_network_execution(args)
    rows = read_csv(args.shortlist)
    layout = CorpusLayout.from_root(args.corpus_root)
    layout.initialize()
    s2_directory = layout.downloaded_from(DownloadSource.SEMANTIC_SCHOLAR)
    openalex_directory = layout.downloaded_from(DownloadSource.OPENALEX)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    s2 = resolve_semantic_scholar(
        [row.get("doi", "") for row in rows],
        api_key=os.getenv(args.semantic_scholar_api_key_env),
    )
    known_hashes = existing_pdf_hashes(s2_directory) | existing_pdf_hashes(
        openalex_directory
    )
    manifest = []
    for index, row in enumerate(rows, start=1):
        doi = normalize_doi(row.get("doi"))
        paper = s2.get(doi) or {}
        oa = paper.get("openAccessPdf") or {}
        s2_url = str(oa.get("url") or "").strip() if isinstance(oa, dict) else ""
        candidates = [("semantic_scholar", s2_url)] if s2_url else []
        if not candidates:
            candidates.extend(("openalex", url) for url in resolve_openalex_urls(doi))
        record = {
            "candidate_rank": row.get("candidate_rank") or index,
            "doi": doi,
            "title": row.get("title", ""),
            "status": "NO_AUTHORIZED_OA_PDF",
            "provider": "",
            "url": "",
            "path": "",
            "sha256": "",
            "bytes": 0,
            "error": "",
        }
        errors = []
        for provider, url in candidates:
            if not url:
                continue
            directory = s2_directory if provider == "semantic_scholar" else openalex_directory
            temporary = output / f"candidate_{index:04d}.pdf.part"
            try:
                digest, size = download_validated_pdf(url, temporary)
                if digest in known_hashes:
                    temporary.unlink(missing_ok=True)
                    record.update(
                        {"status": "DUPLICATE_PDF", "provider": provider, "url": url, "sha256": digest, "bytes": size}
                    )
                    break
                filename = f"{index:04d}-{safe_filename(row.get('title', ''))}.pdf"
                destination = directory / filename
                suffix = 2
                while destination.exists():
                    destination = directory / f"{index:04d}-{safe_filename(row.get('title', ''))}-{suffix}.pdf"
                    suffix += 1
                temporary.replace(destination)
                known_hashes.add(digest)
                record.update(
                    {"status": "DOWNLOADED", "provider": provider, "url": url, "path": str(destination), "sha256": digest, "bytes": size}
                )
                break
            except Exception as exc:
                errors.append(f"{provider}: {type(exc).__name__}: {exc}")
        if errors and record["status"] == "NO_AUTHORIZED_OA_PDF":
            record["status"] = "DOWNLOAD_FAILED"
            record["error"] = " | ".join(errors[:3])
        manifest.append(record)
        atomic_json(output / "download_manifest.json", manifest)
    atomic_csv(output / "download_manifest.csv", manifest)
    counts = {}
    for record in manifest:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    atomic_json(
        output / "summary.json",
        {"status_counts": counts, "llm_called": False, "paywall_bypassed": False},
    )
    print(output)
    return 1 if counts.get("DOWNLOAD_FAILED") else 0


def _prepare_evidence(args: argparse.Namespace) -> int:
    preset = get_preset(args.preset)
    provider_names = tuple(args.provider or preset.evidence_providers)
    if args.with_rag and "physbert" not in provider_names:
        provider_names = (*provider_names, "physbert")
    source = Path(args.csv).resolve()
    frame = read_csv_sanitizing_nul(str(source))
    frame = normalize_legacy_article_frame(
        frame, source_type=args.source_type, source_path=str(source)
    )
    validate_article_frame(frame)
    store = RunStore(args.outputs, args.run_id or _default_run_id(args.preset))
    store.initialize()
    pipeline = EvidencePreparationPipeline(
        target_property=preset.main_extraction_keyword,
        property_keywords=preset.property_keywords,
        rule_patterns=preset.text_candidate_patterns,
        chunk_config=TextChunkConfig(
            target_words=args.target_words,
            max_words=args.max_words,
            overlap_words=args.overlap_words,
        ),
        provider_names=provider_names,
    )
    vector_provider = None
    if "physbert" in provider_names:
        from ..utils.database_manager import VectorDatabaseManager

        rag_path = store.run_dir / "vector_db"
        manager = VectorDatabaseManager(RAGConfig(rag_db_path=str(rag_path)))
        vector_provider = VectorTextEvidenceProvider(CanonicalChunkVectorStore(manager))

    retrieval_queries = preset.extraction_kwargs.get("hybrid_retrieval_queries", [])
    manifest, failures, all_evidence = [], [], []
    for row_number, row in frame.iterrows():
        document_id = str(row["document_id"])
        try:
            chunks, rule_evidence = pipeline.prepare_all(row)
            vector_matches = []
            if vector_provider and chunks:
                vector_provider.index(document_id, chunks)
                vector_matches = vector_provider.select(
                    document_id, retrieval_queries, top_k=args.rag_top_k
                )
            if vector_matches:
                chunks, evidence = pipeline.prepare_all(
                    row, vector_matches=vector_matches
                )
            else:
                evidence = rule_evidence
            status = "PASS" if evidence else "REJECT"
            payload = {
                "document_id": document_id,
                "status": status,
                "chunks": [chunk.to_dict() for chunk in chunks],
                "evidence": [item.to_dict() for item in evidence],
            }
            store.write_json(f"evidence/{_safe_file_stem(document_id)}.json", payload)
            all_evidence.extend(item.to_dict() for item in evidence)
            manifest.append(
                {
                    "row": int(row_number),
                    "document_id": document_id,
                    "status": status,
                    "chunk_count": len(chunks),
                    "evidence_count": len(evidence),
                }
            )
        except Exception as exc:
            failure = {
                "row": int(row_number),
                "document_id": document_id,
                "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
            }
            failures.append(failure)
            manifest.append(failure)

    config = {
        "command": "prepare-evidence",
        "preset": args.preset,
        "source_csv": str(source),
        "with_rag": bool(args.with_rag),
        "evidence_providers": list(provider_names),
        "external_llm_calls": False,
        "chunking": {
            "target_words": args.target_words,
            "max_words": args.max_words,
            "overlap_words": args.overlap_words,
        },
    }
    store.write_json("run_config.json", config)
    store.write_json("manifest.json", manifest)
    store.write_json("evidence/all.json", all_evidence)
    store.write_json("failures.json", failures)
    store.write_json(
        "summary.json",
        {
            "papers": len(manifest),
            "passed": sum(item["status"] == "PASS" for item in manifest),
            "rejected": sum(item["status"] == "REJECT" for item in manifest),
            "errors": len(failures),
            "evidence": len(all_evidence),
        },
    )
    print(store.run_dir)
    return 1 if failures else 0


def _process_articles(args: argparse.Namespace) -> int:
    preset = get_preset(args.preset)
    dois = read_doi_file(args.doi_file)
    plan = build_processing_plan(
        preset=args.preset,
        sources=args.source,
        folder_path=args.folder,
        dois=dois,
        execute_network=args.execute_network,
    )
    print(format_processing_plan(plan))
    if not args.execute_processing:
        return 0
    if plan.network_required and not args.execute_network:
        raise SystemExit(
            "Selected sources require network access. Re-run with both "
            "--execute-processing and --execute-network only after explicit approval."
        )
    execute_processing_plan(
        plan,
        property_keywords=preset.property_keywords,
        main_property_keyword=preset.main_property_keyword,
        processing_kwargs=preset.processing_kwargs,
        dois=dois,
        save_xml=args.save_xml,
        save_pdf=args.save_pdf,
    )
    return 0


def _load_evidence(path: Path) -> list[Evidence]:
    values = json.loads(path.read_text(encoding="utf-8"))
    return [
        Evidence(
            evidence_id=item["evidence_id"],
            document_id=item["document_id"],
            target_property=item["target_property"],
            source_type=EvidenceType(item["source_type"]),
            source_id=item["source_id"],
            content=item["content"],
            retrieval_methods=tuple(
                RetrievalMethod(method["provider"], method.get("details", {}))
                for method in item["retrieval_methods"]
            ),
            section=item.get("section"),
            page_start=item.get("page_start"),
            page_end=item.get("page_end"),
            metadata=item.get("metadata", {}),
        )
        for item in values
    ]


def _scientific_instructions(preset) -> str:
    fields = (
        "composition_property_extraction_agent_notes",
        "composition_property_extraction_task_notes",
    )
    return "\n".join(
        str(preset.extraction_kwargs.get(field, "")).strip()
        for field in fields
        if preset.extraction_kwargs.get(field)
    )


def _extract_evidence(args: argparse.Namespace) -> int:
    if not args.execute:
        raise SystemExit(
            "External model calls are disabled. Re-run with --execute only after explicit approval."
        )
    from ..agents.litellm_adapters import (
        LiteLLMEvidenceExtractor,
        LiteLLMEvidenceIdentifier,
        LiteLLMFigureInterpreter,
        ModelSettings,
    )
    preset = get_preset(args.preset)
    if args.material_normalizer == "material-parser-api" and not args.execute_network:
        raise SystemExit(
            "Material Parser API normalization requires --execute-network."
        )
    store = RunStore(args.outputs, args.run_id)
    evidence_path = store.run_dir / "evidence" / "all.json"
    if not evidence_path.exists():
        raise FileNotFoundError(
            f"Evidence file does not exist; run prepare-evidence first: {evidence_path}"
        )
    prediction_path = store.run_dir / "predictions.json"
    if prediction_path.exists() and not args.force:
        raise FileExistsError(
            f"Predictions already exist: {prediction_path}. Use --force to replace this run output."
        )
    qwen_base = preset.extraction_kwargs.get("identifier_base_url")
    qwen_key_env = preset.extraction_kwargs.get("identifier_api_key_env")
    identifier = LiteLLMEvidenceIdentifier(
        ModelSettings(
            model=args.identifier_model,
            timeout_seconds=args.timeout,
            api_base=qwen_base,
            api_key_env=qwen_key_env,
        ),
        preset.extraction_kwargs["materials_data_identifier_query"],
    )
    extractor = LiteLLMEvidenceExtractor(
        ModelSettings(
            model=args.extractor_model,
            timeout_seconds=args.timeout,
            api_key_env=args.extractor_api_key_env,
        ),
        _scientific_instructions(preset),
    )
    evidence = _load_evidence(evidence_path)
    has_figures = any(item.source_type is EvidenceType.FIGURE for item in evidence)
    figure_interpreter = None
    if has_figures:
        if not args.vision_model:
            raise RuntimeError(
                "This run contains Figure Evidence. Configure --vision-model; "
                "figure pixels are never sent through the text-only route."
            )
        figure_interpreter = LiteLLMFigureInterpreter(
            ModelSettings(
                model=args.vision_model,
                timeout_seconds=args.timeout,
                api_key_env=args.vision_api_key_env,
            )
        )
    results = EvidenceAgentFlow(identifier, extractor, figure_interpreter).run(evidence)
    evidence_by_id = {item.evidence_id: item for item in evidence}
    facts, failures, usage = [], [], []
    for result in results:
        source = evidence_by_id[result.evidence_id]
        usage.append(
            {
                "evidence_id": result.evidence_id,
                "source_type": source.source_type.value,
                "identifier_accepted": (
                    result.decision.accepted
                    if source.source_type is not EvidenceType.FIGURE
                    else None
                ),
                "vlm_called": source.source_type is EvidenceType.FIGURE,
                "extractor_called": result.decision.accepted and result.error is None,
                "error": result.error,
            }
        )
        if result.error:
            failures.append(
                {"evidence_id": result.evidence_id, "error": result.error}
            )
            continue
        for item in result.extracted.get("facts", []):
            if item.get("value") is None or not str(item.get("material_reported", "")).strip():
                continue
            material = str(item["material_reported"]).strip()
            facts.append(
                Fact(
                    document_id=source.document_id,
                    property_name=str(item.get("property") or source.target_property),
                    material_reported=material,
                    material_normalized=material,
                    material_identity_key=material,
                    fact_value=FactValue.from_raw(
                        item["value"],
                        str(item.get("unit", "")),
                        item.get("qualifier"),
                    ),
                    evidence_ids=(source.evidence_id,),
                    conditions=item.get("conditions") or {},
                )
            )
    normalizer = (
        MaterialParserAPINormalizer()
        if args.material_normalizer == "material-parser-api"
        else None
    )
    processor = FactProcessor(normalizer)
    merged = merge_facts(processor.process(fact) for fact in facts)
    store.write_json("predictions.json", [fact.to_dict() for fact in merged])
    store.write_json("failures.json", failures)
    store.write_json("tool_usage.json", usage)
    store.write_json(
        "summary.json",
        {
            "evidence": len(evidence),
            "identifier_accepted": sum(item.decision.accepted for item in results),
            "facts_before_merge": len(facts),
            "facts_after_merge": len(merged),
            "errors": len(failures),
            "material_normalizer": args.material_normalizer,
        },
    )
    return 1 if failures else 0


def _fact_from_dict(item: dict) -> Fact:
    value = item.get("fact_value") or {}
    return Fact(
        document_id=str(item["document_id"]),
        property_name=str(item["property_name"]),
        material_reported=str(item["material_reported"]),
        material_normalized=str(item["material_normalized"]),
        material_identity_key=str(item["material_identity_key"]),
        fact_value=FactValue.from_raw(
            value.get("value", ""), value.get("unit", ""), value.get("qualifier")
        ),
        evidence_ids=tuple(item.get("evidence_ids", [])),
        conditions=item.get("conditions") or {},
    )


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
    print(destination)
    return 0


def _evaluate(args: argparse.Namespace) -> int:
    store = RunStore(args.outputs, args.run_id)
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    predictions = json.loads(
        (store.run_dir / "predictions.json").read_text(encoding="utf-8")
    )
    metrics = score_exact_facts(gold, predictions)
    destination = store.write_json("metrics.json", metrics.to_dict())
    print(destination)
    return 0


_RUN_STAGES = ("prepare", "extract", "review", "evaluate")


def _run_pipeline(args: argparse.Namespace) -> int:
    run_id = args.run_id or _default_run_id(args.preset)
    source_csv = Path(args.csv).resolve() if args.csv else (
        Path(args.outputs).resolve() / "runs" / run_id / "article.csv"
    )
    through_index = _RUN_STAGES.index(args.through)
    plan = {
        "command": "run",
        "run_id": run_id,
        "preset": args.preset,
        "source_csv": str(source_csv),
        "processor_csvs": [str(Path(path).resolve()) for path in args.processor_csv],
        "through": args.through,
        "evidence_providers": list(args.provider or get_preset(args.preset).evidence_providers),
        "material_normalizer": args.material_normalizer,
        "model_calls": through_index >= 1,
        "network_material_normalization": args.material_normalizer == "material-parser-api",
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if not args.execute_pipeline:
        return 0
    if through_index >= 1 and not args.execute_models:
        raise SystemExit("Stages extract/review/evaluate require --execute-models.")
    if through_index >= 3 and not args.gold:
        raise ValueError("--gold is required when --through evaluate")
    if args.material_normalizer == "material-parser-api" and not args.execute_network:
        raise SystemExit("Material Parser API normalization requires --execute-network.")
    if args.processor_csv:
        normalize_article_csvs(args.processor_csv, source_csv, source_type=args.source_type)
    elif not source_csv.is_file():
        raise FileNotFoundError(f"Article CSV does not exist: {source_csv}")

    prepare_args = argparse.Namespace(
        csv=str(source_csv), preset=args.preset, outputs=args.outputs, run_id=run_id,
        source_type=args.source_type, target_words=args.target_words,
        max_words=args.max_words, overlap_words=args.overlap_words,
        with_rag=args.with_rag, rag_top_k=args.rag_top_k, provider=args.provider,
    )
    code = _prepare_evidence(prepare_args)
    if code or through_index == 0:
        return code
    extract_args = argparse.Namespace(
        run_id=run_id, preset=args.preset, outputs=args.outputs,
        identifier_model=args.identifier_model, extractor_model=args.extractor_model,
        extractor_api_key_env=args.extractor_api_key_env,
        vision_model=args.vision_model, vision_api_key_env=args.vision_api_key_env,
        timeout=args.timeout, execute=True, force=args.force,
        material_normalizer=args.material_normalizer,
        execute_network=args.execute_network,
    )
    code = _extract_evidence(extract_args)
    if code or through_index == 1:
        return code
    code = _review(argparse.Namespace(run_id=run_id, outputs=args.outputs))
    if code or through_index == 2:
        return code
    return _evaluate(
        argparse.Namespace(run_id=run_id, outputs=args.outputs, gold=args.gold)
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="comproscanner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("presets", help="List registered property presets")
    subparsers.add_parser("sources", help="List registered article-source adapters")
    corpus = subparsers.add_parser(
        "init-corpus", help="Create separated manual/downloaded/normalized PDF folders"
    )
    corpus.add_argument("--root", default="pdfs")
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
    discover.add_argument("--output", default="outputs/literature/discovery")
    discover.add_argument("--execute-network", action="store_true")
    acquire = subparsers.add_parser(
        "acquire-oa", help="Resolve and download validated OA PDFs"
    )
    acquire.add_argument("--shortlist", required=True)
    acquire.add_argument("--corpus-root", default="pdfs")
    acquire.add_argument("--output", default="outputs/literature/downloads")
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
    prepare.add_argument("--outputs", default="outputs")
    prepare.add_argument("--run-id")
    prepare.add_argument("--source-type", default="unknown")
    prepare.add_argument("--target-words", type=int, default=220)
    prepare.add_argument("--max-words", type=int, default=360)
    prepare.add_argument("--overlap-words", type=int, default=60)
    prepare.add_argument("--with-rag", action="store_true")
    prepare.add_argument(
        "--provider", action="append",
        choices=("rule_text", "physbert", "table", "figure", "equation"),
        help="Override preset Evidence providers; repeat for multiple providers",
    )
    prepare.add_argument("--rag-top-k", type=int, default=3)
    extract = subparsers.add_parser(
        "extract", help="Run Qwen and DeepSeek over prepared Evidence"
    )
    extract.add_argument("--run-id", required=True)
    extract.add_argument("--preset", default="curie_temperature")
    extract.add_argument("--outputs", default="outputs")
    extract.add_argument("--identifier-model", default="openai/qwen-flash")
    extract.add_argument(
        "--extractor-model", default="deepseek/deepseek-v4-flash"
    )
    extract.add_argument("--extractor-api-key-env")
    extract.add_argument(
        "--vision-model",
        help="Required only when the prepared run contains Figure Evidence",
    )
    extract.add_argument("--vision-api-key-env")
    extract.add_argument("--timeout", type=int, default=180)
    extract.add_argument("--execute", action="store_true")
    extract.add_argument("--force", action="store_true")
    extract.add_argument(
        "--material-normalizer",
        choices=("identity", "material-parser-api"),
        default="identity",
    )
    extract.add_argument("--execute-network", action="store_true")
    review = subparsers.add_parser(
        "review", help="Create a one-Fact-per-row workbook with original Evidence"
    )
    review.add_argument("--run-id", required=True)
    review.add_argument("--outputs", default="outputs")
    evaluate = subparsers.add_parser("evaluate", help="Calculate strict TP/FP/FN metrics")
    evaluate.add_argument("--run-id", required=True)
    evaluate.add_argument("--gold", required=True)
    evaluate.add_argument("--outputs", default="outputs")
    run = subparsers.add_parser(
        "run", help="Plan or execute the canonical Article-to-evaluation workflow"
    )
    inputs = run.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--csv", help="Existing canonical or legacy Article CSV")
    inputs.add_argument(
        "--processor-csv", action="append", default=[],
        help="Processor CSV to normalize first; repeat for multiple files",
    )
    run.add_argument("--preset", default="curie_temperature")
    run.add_argument("--run-id")
    run.add_argument("--outputs", default="outputs")
    run.add_argument("--source-type", default="mixed")
    run.add_argument("--through", choices=_RUN_STAGES, default="review")
    run.add_argument("--gold")
    run.add_argument("--provider", action="append", choices=("rule_text", "physbert", "table", "figure", "equation"))
    run.add_argument("--with-rag", action="store_true")
    run.add_argument("--rag-top-k", type=int, default=3)
    run.add_argument("--target-words", type=int, default=220)
    run.add_argument("--max-words", type=int, default=360)
    run.add_argument("--overlap-words", type=int, default=60)
    run.add_argument("--identifier-model", default="openai/qwen-flash")
    run.add_argument("--extractor-model", default="deepseek/deepseek-v4-flash")
    run.add_argument("--extractor-api-key-env")
    run.add_argument("--vision-model")
    run.add_argument("--vision-api-key-env")
    run.add_argument("--timeout", type=int, default=180)
    run.add_argument("--material-normalizer", choices=("identity", "material-parser-api"), default="identity")
    run.add_argument("--execute-pipeline", action="store_true")
    run.add_argument("--execute-models", action="store_true")
    run.add_argument("--execute-network", action="store_true")
    run.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
            normalize_article_csvs(
                args.csv, args.output, source_type=args.source_type
            )
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
    if args.command == "evaluate":
        return _evaluate(args)
    if args.command == "run":
        return _run_pipeline(args)
    raise AssertionError(f"Unhandled command: {args.command}")
