"""Evidence commands for the canonical workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from comproscanner._paths import resolve_recorded_path
from comproscanner.evidence.chunking import TextChunkConfig
from comproscanner.evidence.providers import VectorTextEvidenceProvider
from comproscanner.evidence.vector_store import CanonicalChunkVectorStore
from comproscanner.evidence.preparation import EvidencePreparationPipeline
from comproscanner.presets import get_preset
from comproscanner.results import RunStore
from comproscanner.documents.schemas import normalize_legacy_article_frame
from comproscanner.documents.schemas import validate_article_frame
from comproscanner.evidence.rag.config import RAGConfig
from comproscanner.documents.csv_store import read_csv_sanitizing_nul
from .common import _default_run_id
from .common import _safe_file_stem


def _prepare_evidence(args: argparse.Namespace) -> int:
    preset = get_preset(args.preset)
    provider_names = tuple(args.provider or preset.evidence_providers)
    if args.with_rag and "physbert" not in provider_names:
        provider_names = (*provider_names, "physbert")
    source = resolve_recorded_path(args.csv).resolve()
    frame = read_csv_sanitizing_nul(str(source))
    frame = normalize_legacy_article_frame(
        frame, source_type=args.source_type, source_path=str(source)
    )
    validate_article_frame(frame)
    store = RunStore(args.outputs, args.run_id or _default_run_id(args.preset))
    preparation = {
        "source_csv": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_type": args.source_type,
        "target_property": preset.main_extraction_keyword,
        "property_keywords": preset.property_keywords,
        "text_candidate_patterns": list(preset.text_candidate_patterns),
        "retrieval_queries": list(preset.retrieval_queries),
        "providers": list(provider_names),
        "modality_patterns": {
            key: list(value) for key, value in preset.modality_patterns.items()
        },
        "rag_settings": preset.rag_settings,
        "rag_top_k": args.rag_top_k,
        "chunking": [args.target_words, args.max_words, args.overlap_words],
    }
    saved_config = store.read_json("run_config.json", {})
    previous_preparation = saved_config.get("preparation")
    if getattr(args, "resume", False):
        if previous_preparation and previous_preparation != preparation:
            raise ValueError(
                "Preparation settings or input changed; use a new run-id instead of --resume"
            )
        if (
            not previous_preparation
            and store.evidence_dir.exists()
            and any(store.evidence_dir.glob("*.json"))
        ):
            raise ValueError(
                "Historical Evidence has no preparation configuration; use a new run-id"
            )
        if previous_preparation and (store.evidence_dir / "all.json").is_file():
            manifest = store.read_json("manifest.json", [])
            print(store.run_dir)
            return int(any(item.get("status") == "ERROR" for item in manifest))
    store.initialize()
    store.write_json("run_config.json", {**saved_config, "preparation": preparation})
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
        modality_patterns=preset.modality_patterns,
    )
    vector_provider = None
    if "physbert" in provider_names:
        from comproscanner.evidence.rag.store import VectorDatabaseManager

        rag_path = store.run_dir / "vector_db"
        manager = VectorDatabaseManager(
            RAGConfig(**{**preset.rag_settings, "rag_db_path": str(rag_path)})
        )
        vector_provider = VectorTextEvidenceProvider(CanonicalChunkVectorStore(manager))

    retrieval_queries = preset.retrieval_queries
    manifest, failures, all_evidence = [], [], []
    for row_number, row in frame.iterrows():
        document_id = str(row["document_id"])
        cached_path = store.evidence_dir / f"{_safe_file_stem(document_id)}.json"
        if getattr(args, "resume", False) and cached_path.is_file():
            payload = json.loads(cached_path.read_text(encoding="utf-8"))
            all_evidence.extend(payload.get("evidence", []))
            if payload.get("status") == "ERROR":
                failures.append(payload)
            manifest.append(
                {
                    "row": int(row_number),
                    "document_id": document_id,
                    "status": payload.get("status", "ERROR"),
                    "chunk_count": len(payload.get("chunks", [])),
                    "evidence_count": len(payload.get("evidence", [])),
                    "resumed": True,
                }
            )
            continue
        try:
            chunks, rule_evidence = pipeline.prepare_all(row)
            vector_matches = []
            searchable_chunks = [
                chunk for chunk in chunks if chunk.section != "references"
            ]
            if vector_provider and searchable_chunks:
                vector_provider.index(document_id, searchable_chunks)
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
            store.write_json(
                f"evidence/{_safe_file_stem(document_id)}.json",
                {**failure, "chunks": [], "evidence": []},
            )
            failures.append(failure)
            manifest.append(failure)

    config = {
        **store.read_json("run_config.json", {}),
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
