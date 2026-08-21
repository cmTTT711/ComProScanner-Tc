"""Recover execution coverage for the six failed Tc development papers."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import traceback
import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(r"F:\Python_Project\pdf_analysis\material_agent\input\pdf")
RESULT_DIR = REPO_ROOT / "results" / "tc_benchmark" / "dev_recovery"
RUNTIME_DIR = REPO_ROOT / "work" / "tc_dev_execution_recovery_01_fallback"
RECOVERY_PAPER_IDS = (1, 2, 13, 25, 53, 88)
MODEL = "deepseek/deepseek-v4-flash"
TIMEOUT_SECONDS = 180

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from dotenv import load_dotenv
import pandas as pd
import pymupdf

load_dotenv(REPO_ROOT / ".env")

from comproscanner import ComProScanner
from comproscanner.article_processors import pdfs_processor as pdfs_module
from comproscanner.extract_flow import main_extraction_flow as flow_module
from comproscanner.extract_flow.tools import rag_tool as rag_module
from comproscanner.utils import get_paper_data as paper_data_module
from comproscanner.utils.configs.rag_config import RAGConfig
from comproscanner.utils.database_manager import VectorDatabaseManager
from examples.extract_curie_temperature import get_curie_temperature_preset
from langchain_deepseek import ChatDeepSeek


_active_local_id = ""
_flow_entered = False
_flow_error: BaseException | None = None
_original_kickoff = flow_module.DataExtractionFlow.kickoff
_original_rag_get_llm = rag_module.RAGTool._get_llm


def tc_prefilter_matches(text: str, keywords: dict) -> bool:
    """Use the same deterministic candidate gate as production."""
    from comproscanner.utils.pdf_to_markdown_text import matches_property_keywords

    return matches_property_keywords(text, keywords)


def normalized_pdf_text(pdf_path: Path) -> str:
    """Extract searchable text for local-PDF prefilter recovery only."""
    with pymupdf.open(str(pdf_path)) as document:
        text = "\n".join(page.get_text() for page in document)
    text = text.replace("\u00ad", "")
    text = re.sub(r"\s+", " ", text)
    return text.replace("para electric", "paraelectric")


def recover_empty_section_candidate(
    paper_runtime: Path, pdf_path: Path, keywords: dict, rag_db_path: Path
) -> bool:
    """Create a candidate from raw local text when native sectioning is empty."""
    csv_dir = paper_runtime / "results" / "extracted_data" / "magnetic"
    csv_files = sorted(csv_dir.glob("*.csv"))
    if not csv_files:
        return False
    frame = pd.read_csv(csv_files[0], dtype=str).fillna("")
    if frame.empty or frame["is_property_mentioned"].isin(["1", 1, True]).any():
        return False
    section_columns = [
        "article_title",
        "abstract",
        "introduction",
        "exp_methods",
        "comp_methods",
        "results_discussion",
        "conclusion",
    ]
    if any(frame.iloc[0].get(column, "").strip() for column in section_columns):
        return False

    text = normalized_pdf_text(pdf_path)
    if not tc_prefilter_matches(text, keywords):
        return False
    frame.loc[frame.index[0], "results_discussion"] = text
    frame.loc[frame.index[0], "is_property_mentioned"] = "1"
    frame.to_csv(csv_files[0], index=False)
    VectorDatabaseManager(RAGConfig(rag_db_path=str(rag_db_path))).create_database(
        _active_local_id.replace("/", "_"), text
    )
    return True


def local_benchmark_identifier(paper_id: int) -> str:
    """Return a stable internal key when a local PDF has no trustworthy DOI."""
    return f"10.9999/local-tc-dev-{paper_id:03d}"


def _use_local_identity(self, text: str) -> str:
    return _active_local_id


def _no_crossref_identity(text: str):
    return None


def _offline_metadata(self, doi: str) -> dict:
    return {
        "doi": None,
        "title": "",
        "journal": "",
        "year": "",
        "isOpenAccess": False,
        "authors": [],
        "keywords": [],
    }


def _track_kickoff(self, *args, **kwargs):
    global _flow_entered, _flow_error
    _flow_entered = True
    try:
        return _original_kickoff(self, *args, **kwargs)
    except BaseException as exc:
        _flow_error = exc
        raise


def _deepseek_compatible_get_llm(self):
    model = self.rag_config.rag_chat_model
    if model.startswith("deepseek/"):
        return ChatDeepSeek(
            model=model.split("/", 1)[1],
            request_timeout=1000,
            temperature=0.1,
            streaming=False,
        )
    return _original_rag_get_llm(self)


pdfs_module.PDFsProcessor._extract_doi_from_text = _use_local_identity
pdfs_module.get_doi_from_crossref = _no_crossref_identity
paper_data_module.PaperMetadataExtractor.get_article_metadata = _offline_metadata
flow_module.DataExtractionFlow.kickoff = _track_kickoff
rag_module.RAGTool._get_llm = _deepseek_compatible_get_llm


def find_pdf(paper_id: int) -> Path | None:
    matches = sorted(SOURCE_DIR.glob(f"{paper_id}-*.pdf"))
    return matches[0].resolve() if len(matches) == 1 else None


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def run_paper(paper_id: int, pdf_path: Path | None) -> dict:
    global _active_local_id, _flow_entered, _flow_error
    started = time.perf_counter()
    _active_local_id = local_benchmark_identifier(paper_id)
    _flow_entered = False
    _flow_error = None
    record = {
        "paper_id": paper_id,
        "filename": pdf_path.name if pdf_path else None,
        "pdf_path": str(pdf_path) if pdf_path else None,
        "doi": None,
        "internal_local_id": _active_local_id,
        "entered_tc_extractor": False,
        "status": "PROCESSING_ERROR" if pdf_path is None else None,
        "runtime_seconds": 0.0,
        "output": {},
        "error": "MISSING_PDF" if pdf_path is None else None,
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
            additional_figure_keywords={"exact_keywords": [], "substring_keywords": []},
            failed_pdf_report_path=str(paper_runtime / "failed_pdf_filenames.txt"),
        )
        recover_empty_section_candidate(
            paper_runtime,
            pdf_path,
            preset["property_keywords"],
            paper_runtime / "db",
        )

        native_result = paper_runtime / "prediction.json"
        scanner.extract_composition_property_data(
            **preset["extraction_kwargs"],
            model=MODEL,
            rag_chat_model=MODEL,
            equation_model=MODEL,
            timeout=TIMEOUT_SECONDS,
            rag_db_path=str(paper_runtime / "db"),
            related_figures_base_path=str(
                paper_runtime / "results" / "extracted_data" / "magnetic" / "related_figures"
            ),
            json_results_file=str(native_result),
            checked_doi_list_file=str(paper_runtime / "checked_dois.txt"),
            output_log_folder=str(paper_runtime / "logs"),
            task_output_folder=str(paper_runtime / "task_outputs"),
            is_save_relevant=False,
        )
        output = (
            json.loads(native_result.read_text(encoding="utf-8"))
            if native_result.exists()
            else {}
        )
        record["output"] = output
        record["entered_tc_extractor"] = _flow_entered
        has_values = any(
            bool((item.get("composition_data") or {}).get("compositions_property_values"))
            for item in output.values()
            if isinstance(item, dict)
        )
        if _flow_error and "timeout" in str(_flow_error).lower():
            record["status"] = "API_TIMEOUT"
            record["error"] = f"{type(_flow_error).__name__}: {_flow_error}"
        elif _flow_error:
            record["status"] = "EXTRACTION_ERROR"
            record["error"] = f"{type(_flow_error).__name__}: {_flow_error}"
        elif not _flow_entered:
            record["status"] = "PREFILTER_REJECTED"
        else:
            record["status"] = "COMPLETED" if has_values else "EMPTY_RESULT"
    except (Exception, SystemExit) as exc:
        record["entered_tc_extractor"] = _flow_entered
        record["status"] = "EXTRACTION_ERROR" if _flow_entered else "PROCESSING_ERROR"
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc()
    finally:
        os.chdir(previous_cwd)
        record["runtime_seconds"] = round(time.perf_counter() - started, 3)
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-ids", nargs="+", type=int)
    args = parser.parse_args()
    paper_ids = tuple(args.paper_ids) if args.paper_ids else RECOVERY_PAPER_IDS
    invalid_ids = set(paper_ids) - set(RECOVERY_PAPER_IDS)
    if invalid_ids:
        raise ValueError(f"Only recovery paper IDs are allowed: {sorted(invalid_ids)}")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = RESULT_DIR / "recovery_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = {
            "benchmark": "TC_DEV_EXECUTION_RECOVERY_01",
            "provider": "DeepSeek",
            "model": MODEL,
            "timeout_seconds": TIMEOUT_SECONDS,
            "papers": [],
        }
    records = {item["paper_id"]: item for item in summary["papers"]}
    for paper_id in paper_ids:
        record = run_paper(paper_id, find_pdf(paper_id))
        write_json(RESULT_DIR / f"paper_{paper_id:03d}.json", record)
        records[paper_id] = record
        summary["papers"] = [records[key] for key in sorted(records)]
        write_json(summary_path, summary)
        print(f"PAPER {paper_id}: {record['status']} ({record['runtime_seconds']}s)", flush=True)


if __name__ == "__main__":
    main()
