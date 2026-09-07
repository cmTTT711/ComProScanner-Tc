"""Run commands for the canonical workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from comproscanner.presets import get_preset
from comproscanner.results import RunStore
from comproscanner.documents.ingestion import build_processing_plan
from comproscanner.documents.ingestion import execute_processing_plan
from comproscanner.documents.ingestion import normalize_article_csvs
from comproscanner.documents.ingestion import read_doi_file
from .common import _default_run_id
from .results import _evaluate
from .extraction import _extract_evidence
from .evidence import _prepare_evidence
from .results import _review

_RUN_STAGES = ("prepare", "extract", "review", "evaluate")


def _processor_csv_paths(workspace: Path, preset, plan) -> list[Path]:
    directory = workspace / "results" / "extracted_data" / preset.main_property_keyword
    labels = (
        "pdf" if source in {"manual_pdf", "downloaded_pdf"} else source
        for source in plan.requested_sources
    )
    paths = [
        directory / f"{label}_{preset.main_property_keyword}_paragraphs.csv"
        for label in dict.fromkeys(labels)
    ]
    return [path for path in paths if path.is_file()]


def _run_stage(
    store: RunStore, name: str, action, *, resume: bool, artifact: Path | None = None
):
    if (
        resume
        and store.stage_completed(name)
        and (artifact is None or artifact.exists())
    ):
        return 0
    store.update_stage(name, "RUNNING")
    try:
        code = action()
    except Exception as exc:
        store.update_stage(name, "ERROR", error=f"{type(exc).__name__}: {exc}")
        raise
    status = "COMPLETE" if not code else "COMPLETE_WITH_ERRORS"
    store.update_stage(name, status, exit_code=int(code or 0))
    return int(code or 0)


def _run_pipeline(args: argparse.Namespace) -> int:
    if args.resume and args.force:
        raise ValueError("--resume and --force cannot be used together")
    run_id = args.run_id or _default_run_id(args.preset)
    source_csv = (
        Path(args.csv).resolve()
        if args.csv
        else (Path(args.outputs).resolve() / "runs" / run_id / "article.csv")
    )
    through_index = _RUN_STAGES.index(args.through)
    preset = get_preset(args.preset)
    dois = read_doi_file(args.doi_file) if args.source else None
    processing_plan = None
    if args.source:
        processing_plan = build_processing_plan(
            preset=args.preset,
            sources=args.source,
            folder_path=args.folder,
            dois=dois,
            execute_network=args.execute_network,
        )
    plan = {
        "command": "run",
        "run_id": run_id,
        "preset": args.preset,
        "source_csv": str(source_csv),
        "processor_csvs": [str(Path(path).resolve()) for path in args.processor_csv],
        "article_sources": list(args.source or []),
        "article_processing": processing_plan.to_dict() if processing_plan else None,
        "through": args.through,
        "evidence_providers": list(
            args.provider or get_preset(args.preset).evidence_providers
        ),
        "material_normalizer": args.material_normalizer,
        "model_calls": through_index >= 1,
        "network_material_normalization": args.material_normalizer
        == "material-parser-api",
        "resume": bool(args.resume),
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if not args.execute_pipeline:
        return 0
    if through_index >= 1 and not args.execute_models:
        raise SystemExit("Stages extract/review/evaluate require --execute-models.")
    if through_index >= 3 and not args.gold:
        raise ValueError("--gold is required when --through evaluate")
    if args.material_normalizer == "material-parser-api" and not args.execute_network:
        raise SystemExit(
            "Material Parser API normalization requires --execute-network."
        )
    if (
        processing_plan
        and processing_plan.network_required
        and not args.execute_network
    ):
        raise SystemExit(
            "Selected article sources require --execute-network before processing."
        )

    store = RunStore(args.outputs, run_id)
    store.initialize()
    # Check supplied inputs before normalization/processing can replace this
    # run's Article while leaving old Evidence and predictions beside it.
    input_paths = [Path(path).resolve() for path in args.processor_csv]
    if args.source and args.folder:
        folder = Path(args.folder).resolve()
        input_paths.extend(sorted(folder.rglob("*.pdf")))
    input_config = {
        "files": [
            {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in input_paths
        ],
        "sources": list(args.source or []),
        "folder": str(Path(args.folder).resolve()) if args.folder else None,
        "dois": dois,
    }
    saved_config = store.read_json("run_config.json", {})
    if (
        args.resume
        and saved_config.get("inputs")
        and saved_config["inputs"] != input_config
    ):
        raise ValueError(
            "Preparation settings or input changed; use a new run-id instead of --resume"
        )
    store.write_json("run_config.json", {**saved_config, "inputs": input_config})
    failures_seen = False
    if processing_plan:
        workspace = store.run_dir / "processor_workspace"

        def process_sources():
            workspace.mkdir(parents=True, exist_ok=True)
            previous = Path.cwd()
            try:
                os.chdir(workspace)
                execute_processing_plan(
                    processing_plan,
                    property_keywords=preset.property_keywords,
                    main_property_keyword=preset.main_property_keyword,
                    processing_kwargs=preset.processing_kwargs,
                    dois=dois,
                    save_xml=args.save_xml,
                    save_pdf=args.save_pdf,
                )
            finally:
                os.chdir(previous)
            if not _processor_csv_paths(workspace, preset, processing_plan):
                raise FileNotFoundError(
                    "Article processing completed without producing an expected processor CSV"
                )
            return 0

        _run_stage(store, "process", process_sources, resume=args.resume)

        def normalize_processed():
            paths = _processor_csv_paths(workspace, preset, processing_plan)
            if not paths:
                raise FileNotFoundError(
                    "No processor CSV is available for normalization"
                )
            normalize_article_csvs(
                paths, source_csv, source_type=args.source_type, source_root=workspace
            )
            return 0

        _run_stage(
            store,
            "normalize",
            normalize_processed,
            resume=args.resume,
            artifact=source_csv,
        )
    elif args.processor_csv:

        def normalize_supplied():
            normalize_article_csvs(
                args.processor_csv, source_csv, source_type=args.source_type
            )
            return 0

        _run_stage(
            store,
            "normalize",
            normalize_supplied,
            resume=False,
            artifact=source_csv,
        )
    elif not source_csv.is_file():
        raise FileNotFoundError(f"Article CSV does not exist: {source_csv}")

    prepare_args = argparse.Namespace(
        csv=str(source_csv),
        preset=args.preset,
        outputs=args.outputs,
        run_id=run_id,
        source_type=args.source_type,
        target_words=args.target_words,
        max_words=args.max_words,
        overlap_words=args.overlap_words,
        with_rag=args.with_rag,
        rag_top_k=args.rag_top_k,
        provider=args.provider,
        resume=args.resume,
    )
    code = _run_stage(
        store,
        "prepare",
        lambda: _prepare_evidence(prepare_args),
        resume=False,
        artifact=store.evidence_dir / "all.json",
    )
    failures_seen |= bool(code)
    if through_index == 0:
        return int(failures_seen)
    extract_args = argparse.Namespace(
        run_id=run_id,
        preset=args.preset,
        outputs=args.outputs,
        identifier_model=args.identifier_model,
        extractor_model=args.extractor_model,
        identifier_base_url=args.identifier_base_url,
        identifier_api_key_env=args.identifier_api_key_env,
        extractor_base_url=args.extractor_base_url,
        extractor_api_key_env=args.extractor_api_key_env,
        vision_model=args.vision_model,
        vision_api_key_env=args.vision_api_key_env,
        vision_base_url=args.vision_base_url,
        timeout=args.timeout,
        execute=True,
        force=args.force,
        material_normalizer=args.material_normalizer,
        execute_network=args.execute_network,
        resume=args.resume,
    )
    code = _run_stage(
        store,
        "extract",
        lambda: _extract_evidence(extract_args),
        # Extraction validates its saved configuration before reusing per-Evidence
        # checkpoints or predictions, including when this stage already completed.
        resume=False,
        artifact=store.run_dir / "predictions.json",
    )
    failures_seen |= bool(code)
    if through_index == 1:
        return int(failures_seen)
    _run_stage(
        store,
        "review",
        lambda: _review(argparse.Namespace(run_id=run_id, outputs=args.outputs)),
        resume=args.resume,
        artifact=store.run_dir / "review.xlsx",
    )
    if through_index == 2:
        return int(failures_seen)
    _run_stage(
        store,
        "evaluate",
        lambda: _evaluate(
            argparse.Namespace(
                run_id=run_id,
                outputs=args.outputs,
                gold=args.gold,
                preset=args.preset,
                paper_map=args.paper_map,
            )
        ),
        resume=args.resume,
        artifact=store.run_dir / "metrics.json",
    )
    return int(failures_seen)
