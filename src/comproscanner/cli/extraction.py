"""Extraction commands for the canonical workflow."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from comproscanner.extraction import EvidenceAgentFlow
from comproscanner.extraction import EvidenceDecision
from comproscanner.extraction import EvidenceExtraction
from comproscanner.evidence import EvidenceType
from comproscanner.presets import get_preset
from comproscanner.results import RunStore
from comproscanner.results.facts import Fact
from comproscanner.results.facts import FactValue
from comproscanner.results.facts import merge_facts
from .common import _load_evidence
from .results import _material_article_config
from .results import _material_processor
from .common import _safe_file_stem


def _scientific_instructions(preset) -> str:
    instructions = preset.extraction_instructions
    if preset.examples:
        instructions += (
            "\n\nILLUSTRATIVE EXAMPLES (not evidence for the current article; "
            "never copy their materials or values into the answer):\n"
            + json.dumps(preset.examples, ensure_ascii=False, indent=2)
        )
    return instructions


def _extraction_config(args, preset, evidence_path: Path) -> dict:
    """Record reproducible settings without reading or storing API secrets."""
    return {
        "preset": preset.name,
        "evidence_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        "identifier_query": preset.identifier_query,
        "extraction_instructions": _scientific_instructions(preset),
        "allowed_units": list(preset.allowed_units),
        "required_conditions": list(preset.required_conditions),
        "material_normalizer": args.material_normalizer,
        "material_article": _material_article_config(
            args, RunStore(args.outputs, args.run_id)
        ),
        "timeout": args.timeout,
        "agent_prompts": asdict(preset.agent_prompts),
        "fact_fields": preset.fact_fields,
        "models": {
            role: {
                "model": getattr(args, f"{role}_model"),
                "base_url": getattr(args, f"{role}_base_url"),
                "api_key_env": getattr(args, f"{role}_api_key_env"),
                "parameters": preset.models[role].get("parameters", {}),
            }
            for role in ("identifier", "extractor", "vision")
        },
    }


def _extract_evidence(args: argparse.Namespace) -> int:
    if getattr(args, "resume", False) and args.force:
        raise ValueError("--resume and --force cannot be used together")
    if not args.execute:
        raise SystemExit(
            "External model calls are disabled. Re-run with --execute only after explicit approval."
        )
    from comproscanner.extraction.litellm_adapters import LiteLLMEvidenceExtractor
    from comproscanner.extraction.litellm_adapters import LiteLLMEvidenceIdentifier
    from comproscanner.extraction.litellm_adapters import LiteLLMFigureInterpreter
    from comproscanner.extraction.litellm_adapters import ModelSettings

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
    evidence = _load_evidence(evidence_path)
    if any(
        item.target_property.casefold() != preset.main_extraction_keyword.casefold()
        for item in evidence
    ):
        raise ValueError("Prepared Evidence belongs to a different property preset")
    config = store.read_json("run_config.json", {})
    extraction_config = _extraction_config(args, preset, evidence_path)
    previous_config = config.get("extraction")
    if (
        getattr(args, "resume", False)
        and previous_config
        and previous_config != extraction_config
    ):
        raise ValueError(
            "Extraction settings or Evidence changed; use a new run-id instead of --resume"
        )
    if prediction_path.exists() and getattr(args, "resume", False):
        print(prediction_path)
        return int(bool(store.read_json("failures.json", [])))
    if prediction_path.exists() and not args.force:
        raise FileExistsError(
            f"Predictions already exist: {prediction_path}. Use --force to replace this run output."
        )
    config["extraction"] = extraction_config
    store.write_json("run_config.json", config)
    identifier = LiteLLMEvidenceIdentifier(
        ModelSettings(
            model=args.identifier_model,
            timeout_seconds=args.timeout,
            api_base=args.identifier_base_url,
            api_key_env=args.identifier_api_key_env,
            parameters=preset.models["identifier"].get("parameters", {}),
        ),
        preset.identifier_query,
        prompts=preset.agent_prompts,
    )
    extractor = LiteLLMEvidenceExtractor(
        ModelSettings(
            model=args.extractor_model,
            timeout_seconds=args.timeout,
            api_base=args.extractor_base_url,
            api_key_env=args.extractor_api_key_env,
            parameters=preset.models["extractor"].get("parameters", {}),
        ),
        _scientific_instructions(preset),
        prompts=preset.agent_prompts,
        fact_fields=preset.fact_fields,
    )
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
                api_base=args.vision_base_url,
                api_key_env=args.vision_api_key_env,
                parameters=preset.models["vision"].get("parameters", {}),
            ),
            prompts=preset.agent_prompts,
        )
    flow = EvidenceAgentFlow(identifier, extractor, figure_interpreter)
    results = []
    for item in evidence:
        cache_name = f"papers/{_safe_file_stem(item.evidence_id)}.json"
        cached = store.read_json(cache_name) if getattr(args, "resume", False) else None
        if cached is not None:
            decision_data = cached.get("decision", {})
            results.append(
                EvidenceExtraction(
                    evidence_id=item.evidence_id,
                    decision=EvidenceDecision(
                        item.evidence_id,
                        bool(decision_data.get("accepted")),
                        str(decision_data.get("raw_response", "")),
                    ),
                    extracted=cached.get("extracted", {}),
                    error=cached.get("error"),
                )
            )
            continue
        result = flow.run([item])[0]
        store.write_json(
            cache_name,
            {
                "evidence_id": result.evidence_id,
                "decision": {
                    "accepted": result.decision.accepted,
                    "raw_response": result.decision.raw_response,
                },
                "extracted": result.extracted,
                "error": result.error,
            },
        )
        results.append(result)
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
            failures.append({"evidence_id": result.evidence_id, "error": result.error})
            continue
        for index, item in enumerate(result.extracted.get("facts", [])):
            if (
                not isinstance(item, dict)
                or item.get("value") is None
                or isinstance(item.get("value"), bool)
                or not isinstance(item.get("value"), (str, int, float))
                or not str(item.get("value", "")).strip()
                or not str(item.get("material_reported") or "").strip()
                or not isinstance(item.get("conditions") or {}, dict)
                or not isinstance(item.get("qualifier"), (str, type(None)))
            ):
                failures.append(
                    {
                        "evidence_id": result.evidence_id,
                        "fact_index": index,
                        "error": "Invalid Fact: require material, scalar value, object conditions and string/null qualifier",
                        "raw_fact": item,
                    }
                )
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
                    attributes={
                        k: v
                        for k, v in item.items()
                        if k
                        not in {
                            "material_reported",
                            "property",
                            "value",
                            "unit",
                            "qualifier",
                            "conditions",
                        }
                    },
                )
            )
    abbreviations = {}
    for result in results:
        document_id = evidence_by_id[result.evidence_id].document_id
        mapping = result.extracted.get("abbreviations") or {}
        for alias, formula in (mapping.items() if isinstance(mapping, dict) else ()):
            if isinstance(formula, str):
                abbreviations.setdefault(document_id, {}).setdefault(alias, []).append(
                    formula
                )
    processor = _material_processor(args, store, evidence, abbreviations)
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
            "facts_needing_review": sum(
                bool(fact.processing_issues) for fact in merged
            ),
            "material_normalizer": args.material_normalizer,
        },
    )
    return 1 if failures else 0
