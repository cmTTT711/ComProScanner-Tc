"""Run the Tc Hybrid+Qwen extraction on local Papers 1-100.

The runner is deliberately resumable: a completed per-paper JSON is never
re-sent unless ``--force`` is explicitly supplied. One paper failure does not
stop later papers. Runtime artifacts stay under ``work``; only predictions and
the compact run summary are written to ``outputs``.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

import pandas as pd
import pymupdf


REPO_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = REPO_ROOT / "pdfs"
OUTPUT_DIR = REPO_ROOT / "outputs" / "tc_hybrid_qwen_001_030"
RUNTIME_DIR = REPO_ROOT / "work" / "tc_hybrid_qwen_001_030"
PAPER_IDS = tuple(range(1, 101))
DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash"
TIMEOUT_SECONDS = 180

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(REPO_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from comproscanner import ComProScanner
from comproscanner.presets.curie_temperature import get_curie_temperature_preset
from comproscanner.utils.configs.rag_config import RAGConfig
from comproscanner.utils.database_manager import VectorDatabaseManager
from comproscanner.utils.pdf_to_markdown_text import matches_property_keywords


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def find_pdf(paper_id: int) -> Path | None:
    pattern = re.compile(rf"^{paper_id}-")
    matches = sorted(
        path.resolve()
        for path in PDF_DIR.glob("*.pdf")
        if pattern.match(path.name)
    )
    if len(matches) > 1:
        raise ValueError(
            f"Paper {paper_id} has multiple PDF matches: "
            + ", ".join(path.name for path in matches)
        )
    return matches[0] if matches else None


def _has_values(output: dict) -> bool:
    return any(
        bool((record.get("composition_data") or {}).get("compositions_property_values"))
        for record in output.values()
        if isinstance(record, dict)
    )


def recover_raw_text_candidate(
    paper_runtime: Path, pdf_path: Path, property_keywords: dict
) -> bool:
    """Recover a deterministic candidate when structured PDF sections miss Tc.

    This is the same high-recall principle used by the accepted 30-paper run:
    only a local regex/keyword match can promote the paper, and the LLM is not
    consulted during recovery.
    """
    csv_dir = paper_runtime / "results" / "extracted_data" / "magnetic"
    csv_files = sorted(csv_dir.glob("*.csv"))
    if not csv_files:
        return False
    frame = pd.read_csv(csv_files[0], dtype=str).fillna("")
    if frame.empty or frame["is_property_mentioned"].isin(["1", 1, True]).any():
        return False

    with pymupdf.open(str(pdf_path)) as document:
        raw_text = "\n".join(page.get_text() for page in document)
    raw_text = raw_text.replace("\u00ad", "")
    raw_text = re.sub(r"\s+", " ", raw_text).replace(
        "para electric", "paraelectric"
    )
    if not matches_property_keywords(raw_text, property_keywords):
        return False

    row_index = frame.index[0]
    frame.loc[row_index, "results_discussion"] = raw_text
    frame.loc[row_index, "is_property_mentioned"] = "1"
    frame.to_csv(csv_files[0], index=False)
    document_id = str(frame.loc[row_index, "doi"])
    db_name = document_id.replace("/", "_").replace(":", "_")
    manager = VectorDatabaseManager(
        RAGConfig(rag_db_path=str(paper_runtime / "db"))
    )
    if not manager.database_exists(db_name):
        manager.create_database(db_name=db_name, article_text=raw_text)
    return True


def run_paper(paper_id: int, pdf_path: Path | None) -> dict:
    started = time.perf_counter()
    record = {
        "paper_id": paper_id,
        "filename": pdf_path.name if pdf_path else None,
        "pdf_path": str(pdf_path) if pdf_path else None,
        "status": "MISSING_PDF" if pdf_path is None else "PROCESSING",
        "runtime_seconds": 0.0,
        "output": {},
        "error": None,
        "attempt_count": 1,
    }
    if pdf_path is None:
        return record

    paper_runtime = RUNTIME_DIR / f"paper_{paper_id:03d}"
    input_dir = paper_runtime / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    staged_pdf = input_dir / pdf_path.name
    if not staged_pdf.exists():
        shutil.copy2(pdf_path, staged_pdf)

    previous_cwd = Path.cwd()
    stage = "processing"
    try:
        os.chdir(paper_runtime)
        preset = get_curie_temperature_preset()
        scanner = ComProScanner(main_property_keyword=preset["main_property_keyword"])
        scanner.process_articles(
            property_keywords=preset["property_keywords"],
            source_list=["pdfs"],
            folder_path=str(input_dir),
            rag_db_path=str(paper_runtime / "db"),
            main_figure_keywords={"exact_keywords": [], "substring_keywords": []},
            additional_figure_keywords={
                "exact_keywords": [],
                "substring_keywords": [],
            },
            failed_pdf_report_path=str(paper_runtime / "failed_pdfs.txt"),
            **preset["processing_kwargs"],
        )
        record["raw_text_candidate_recovered"] = recover_raw_text_candidate(
            paper_runtime,
            pdf_path,
            preset["property_keywords"],
        )

        stage = "extraction"
        native_result = paper_runtime / "prediction.json"
        scanner.extract_composition_property_data(
            **preset["extraction_kwargs"],
            model=DEEPSEEK_MODEL,
            rag_chat_model=DEEPSEEK_MODEL,
            equation_model=DEEPSEEK_MODEL,
            timeout=TIMEOUT_SECONDS,
            rag_db_path=str(paper_runtime / "db"),
            related_figures_base_path=str(
                paper_runtime
                / "results"
                / "extracted_data"
                / "magnetic"
                / "related_figures"
            ),
            json_results_file=str(native_result),
            checked_doi_list_file=str(paper_runtime / "checked_dois.txt"),
            is_save_relevant=False,
            verbose=False,
        )
        output = (
            json.loads(native_result.read_text(encoding="utf-8"))
            if native_result.exists()
            else {}
        )
        record["output"] = output
        reports = getattr(scanner, "last_extraction_report", [])
        if reports:
            record["pipeline_report"] = reports
        flow_errors = [
            report
            for report in reports
            if isinstance(report, dict) and report.get("status") == "FLOW_ERROR"
        ]
        if flow_errors:
            error_text = " | ".join(str(item.get("error") or "") for item in flow_errors)
            record["status"] = (
                "EXTRACTION_TIMEOUT"
                if "timeout" in error_text.casefold()
                else "EXTRACTION_ERROR"
            )
            record["error"] = error_text or "Extraction flow failed"
        elif not output and not reports:
            record["status"] = "PREFILTER_REJECTED"
        else:
            record["status"] = "COMPLETED" if _has_values(output) else "EMPTY_RESULT"
    except (Exception, SystemExit) as exc:
        record["status"] = (
            "PROCESSING_ERROR" if stage == "processing" else "EXTRACTION_ERROR"
        )
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc()
    finally:
        os.chdir(previous_cwd)
        record["runtime_seconds"] = round(time.perf_counter() - started, 3)
        gc.collect()
    return record


def compact_predictions(records: list[dict]) -> dict:
    return {
        "task": "TC_HYBRID_QWEN_001_100",
        "candidate_mode": "hybrid_rule_plus_physbert",
        "identifier_model": "qwen-flash",
        "extraction_model": DEEPSEEK_MODEL,
        "timeout_seconds": TIMEOUT_SECONDS,
        "attempts_per_paper": 1,
        "papers": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-ids", nargs="+", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    paper_ids = tuple(args.paper_ids) if args.paper_ids else PAPER_IDS
    invalid = sorted(set(paper_ids) - set(PAPER_IDS))
    if invalid:
        raise ValueError(f"Only Paper 1-100 are allowed: {invalid}")

    mappings = {paper_id: find_pdf(paper_id) for paper_id in paper_ids}
    missing = [paper_id for paper_id, path in mappings.items() if path is None]
    if missing:
        raise FileNotFoundError(f"Missing PDF mappings: {missing}")
    if args.validate_only:
        print(f"Validated {len(mappings)} unique Paper 1-100 PDF mappings.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    per_paper_dir = OUTPUT_DIR / "papers"
    per_paper_dir.mkdir(parents=True, exist_ok=True)
    records: dict[int, dict] = {}
    for existing in per_paper_dir.glob("paper_*.json"):
        item = json.loads(existing.read_text(encoding="utf-8"))
        records[int(item["paper_id"])] = item

    for paper_id in paper_ids:
        if paper_id in records and not args.force:
            print(
                f"PAPER {paper_id}: SKIPPED_EXISTING ({records[paper_id]['status']})",
                flush=True,
            )
            continue
        record = run_paper(paper_id, mappings[paper_id])
        records[paper_id] = record
        write_json(per_paper_dir / f"paper_{paper_id:03d}.json", record)
        ordered = [records[key] for key in sorted(records)]
        write_json(OUTPUT_DIR / "predictions_001_100.json", compact_predictions(ordered))
        write_json(
            OUTPUT_DIR / "run_summary.json",
            {
                "task": "TC_HYBRID_QWEN_001_100",
                "completed_papers": len(ordered),
                "status_counts": {
                    status: sum(item["status"] == status for item in ordered)
                    for status in sorted({item["status"] for item in ordered})
                },
                "total_runtime_seconds": round(
                    sum(item.get("runtime_seconds", 0) for item in ordered), 3
                ),
            },
        )
        print(
            f"PAPER {paper_id}: {record['status']} "
            f"({record['runtime_seconds']}s)",
            flush=True,
        )


if __name__ == "__main__":
    main()
