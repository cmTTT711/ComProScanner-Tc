"""Run the frozen Curie-temperature preset on the ten-paper development set."""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(r"F:\Python_Project\pdf_analysis\material_agent\input\pdf")
RESULT_DIR = REPO_ROOT / "results" / "tc_benchmark" / "dev"
RUNTIME_DIR = REPO_ROOT / "work" / "tc_benchmark_dev_01_utf8"
DEV_PAPER_IDS = (1, 2, 4, 13, 25, 42, 53, 76, 78, 88)
MODEL = "deepseek/deepseek-v4-flash"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from comproscanner import ComProScanner
from comproscanner.extract_flow.tools import rag_tool as rag_module
from comproscanner.presets.curie_temperature import get_curie_temperature_preset
from langchain_deepseek import ChatDeepSeek


# ChatDeepSeek expects the provider prefix to be removed. This adapts only the
# runner's RAG client; the Tc preset and ComProScanner source remain unchanged.
_original_get_llm = rag_module.RAGTool._get_llm


def _deepseek_compatible_get_llm(self):
    model = self.rag_config.rag_chat_model
    if model.startswith("deepseek/"):
        return ChatDeepSeek(
            model=model.split("/", 1)[1],
            request_timeout=1000,
            temperature=0.1,
            streaming=False,
        )
    return _original_get_llm(self)


rag_module.RAGTool._get_llm = _deepseek_compatible_get_llm


def find_pdf(paper_id: int) -> Path | None:
    matches = sorted(SOURCE_DIR.glob(f"{paper_id}-*.pdf"))
    return matches[0].resolve() if len(matches) == 1 else None


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def classify_error(exc: BaseException, stage: str) -> str:
    message = str(exc).lower()
    if any(token in message for token in ("api", "rate limit", "authentication", "timeout", "connection")):
        return "API_ERROR"
    return "PROCESSING_ERROR" if stage == "processing" else "EXTRACTION_ERROR"


def run_paper(paper_id: int, pdf_path: Path | None) -> dict:
    started = time.perf_counter()
    record = {
        "paper_id": paper_id,
        "filename": pdf_path.name if pdf_path else None,
        "pdf_path": str(pdf_path) if pdf_path else None,
        "status": "MISSING_PDF" if pdf_path is None else None,
        "runtime_seconds": 0.0,
        "output": {},
        "error": None,
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
            additional_figure_keywords={"exact_keywords": [], "substring_keywords": []},
            failed_pdf_report_path=str(paper_runtime / "failed_pdf_filenames.txt"),
            **preset["processing_kwargs"],
        )

        stage = "extraction"
        native_result = paper_runtime / "prediction.json"
        scanner.extract_composition_property_data(
            **preset["extraction_kwargs"],
            model=MODEL,
            rag_chat_model=MODEL,
            equation_model=MODEL,
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
        output = json.loads(native_result.read_text(encoding="utf-8")) if native_result.exists() else {}
        record["output"] = output
        has_values = any(
            bool((item.get("composition_data") or {}).get("compositions_property_values"))
            for item in output.values()
            if isinstance(item, dict)
        )
        record["status"] = "COMPLETED" if has_values else "EMPTY_RESULT"
    except (Exception, SystemExit) as exc:
        record["status"] = classify_error(exc, stage)
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc()
    finally:
        os.chdir(previous_cwd)
        record["runtime_seconds"] = round(time.perf_counter() - started, 3)
    return record


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    mappings = {paper_id: find_pdf(paper_id) for paper_id in DEV_PAPER_IDS}
    summary = {
        "benchmark": "TC_DEV_BENCHMARK_01",
        "provider": "DeepSeek",
        "model": MODEL,
        "papers": [],
    }
    for paper_id in DEV_PAPER_IDS:
        record = run_paper(paper_id, mappings[paper_id])
        write_json(RESULT_DIR / f"paper_{paper_id:03d}.json", record)
        summary["papers"].append(record)
        write_json(RESULT_DIR / "dev_summary.json", summary)
        print(f"PAPER {paper_id}: {record['status']} ({record['runtime_seconds']}s)", flush=True)


if __name__ == "__main__":
    main()
