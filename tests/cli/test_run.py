import json
import importlib
from pathlib import Path

import pandas as pd
import pytest

from comproscanner.cli.main import main

cli_main = importlib.import_module("comproscanner.cli.run")
from comproscanner.evidence.preparation import EvidencePreparationPipeline


def test_run_defaults_to_inert_plan_for_missing_input(tmp_path, capsys):
    missing = tmp_path / "not-created.csv"
    assert main(["run", "--csv", str(missing), "--run-id", "planned"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["run_id"] == "planned"
    assert plan["through"] == "review"
    assert not missing.exists()


def test_run_requires_model_execution_before_any_pipeline_side_effect(tmp_path):
    with pytest.raises(SystemExit, match="require --execute-models"):
        main(
            [
                "run",
                "--csv",
                str(tmp_path / "missing.csv"),
                "--run-id",
                "blocked",
                "--execute-pipeline",
            ]
        )
    assert not (tmp_path / "outputs").exists()


def test_run_can_normalize_and_prepare_locally_without_models(tmp_path):
    source = tmp_path / "processor.csv"
    pd.DataFrame(
        [
            {
                "doi": "10.1/test",
                "article_title": "BFO",
                "abstract": "BiFeO3 has a Curie temperature of 1103 K.",
                "introduction": "",
                "exp_methods": "",
                "comp_methods": "",
                "results_discussion": "",
                "conclusion": "",
                "is_property_mentioned": "1",
            }
        ]
    ).to_csv(source, index=False)
    outputs = tmp_path / "outputs"
    assert (
        main(
            [
                "run",
                "--processor-csv",
                str(source),
                "--run-id",
                "local",
                "--outputs",
                str(outputs),
                "--through",
                "prepare",
                "--execute-pipeline",
            ]
        )
        == 0
    )
    run = outputs / "runs" / "local"
    assert (run / "article.csv").is_file()
    assert (run / "evidence" / "all.json").is_file()
    assert not (run / "predictions.json").exists()


def test_extract_material_parser_requires_explicit_network_permission():
    with pytest.raises(SystemExit, match="requires --execute-network"):
        main(
            [
                "extract",
                "--run-id",
                "x",
                "--execute",
                "--material-normalizer",
                "material-parser-api",
            ]
        )


def test_run_raw_pdf_plan_is_inert(tmp_path, monkeypatch, capsys):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(cli_main, "execute_processing_plan", forbidden)
    assert (
        main(
            [
                "run",
                "--source",
                "manual_pdf",
                "--folder",
                str(pdfs),
                "--run-id",
                "planned-pdf",
                "--outputs",
                str(tmp_path / "outputs"),
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert plan["article_sources"] == ["manual_pdf"]
    assert not called
    assert not (tmp_path / "outputs").exists()


def test_run_network_source_is_blocked_before_side_effects(tmp_path):
    outputs = tmp_path / "outputs"
    with pytest.raises(SystemExit, match="require --execute-network"):
        main(
            [
                "run",
                "--source",
                "elsevier",
                "--run-id",
                "blocked-network",
                "--outputs",
                str(outputs),
                "--through",
                "prepare",
                "--execute-pipeline",
            ]
        )
    assert not outputs.exists()


def test_run_processes_raw_pdf_in_isolated_workspace_and_restores_cwd(
    tmp_path, monkeypatch
):
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    outputs = tmp_path / "outputs"
    original_cwd = Path.cwd()

    def fake_execute(plan, *, main_property_keyword, **kwargs):
        destination = Path.cwd() / "results" / "extracted_data" / main_property_keyword
        destination.mkdir(parents=True)
        pd.DataFrame(
            [
                {
                    "doi": "10.1/raw",
                    "article_title": "Raw PDF",
                    "abstract": "BiFeO3 has a Curie temperature of 1103 K.",
                }
            ]
        ).to_csv(
            destination / f"pdf_{main_property_keyword}_paragraphs.csv", index=False
        )

    monkeypatch.setattr(cli_main, "execute_processing_plan", fake_execute)
    assert (
        main(
            [
                "run",
                "--source",
                "manual_pdf",
                "--folder",
                str(pdfs),
                "--run-id",
                "raw",
                "--outputs",
                str(outputs),
                "--through",
                "prepare",
                "--execute-pipeline",
            ]
        )
        == 0
    )
    run = outputs / "runs" / "raw"
    assert (run / "article.csv").is_file()
    assert (run / "evidence" / "all.json").is_file()
    assert Path.cwd() == original_cwd
    stages = json.loads((run / "stage_status.json").read_text(encoding="utf-8"))
    assert stages["process"]["status"] == "COMPLETE"
    assert stages["normalize"]["status"] == "COMPLETE"
    assert stages["prepare"]["status"] == "COMPLETE"


def test_run_resume_skips_completed_prepare_stage(tmp_path, monkeypatch):
    source = tmp_path / "article.csv"
    pd.DataFrame(
        [
            {
                "doi": "10.1/resume",
                "article_title": "Resume",
                "abstract": "BiFeO3 has a Curie temperature of 1103 K.",
            }
        ]
    ).to_csv(source, index=False)
    outputs = tmp_path / "outputs"
    argv = [
        "run",
        "--csv",
        str(source),
        "--run-id",
        "resume",
        "--outputs",
        str(outputs),
        "--through",
        "prepare",
        "--execute-pipeline",
    ]
    assert main(argv) == 0

    def forbidden(*_args, **_kwargs):
        raise AssertionError("completed prepare stage should be skipped")

    monkeypatch.setattr(EvidencePreparationPipeline, "prepare_all", forbidden)
    assert main([*argv, "--resume"]) == 0


def test_run_rejects_force_and_resume_together(tmp_path):
    source = tmp_path / "article.csv"
    source.write_text("document_id,title,full_text\n1,A,Tc 400 K\n", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot be used together"):
        main(
            [
                "run",
                "--csv",
                str(source),
                "--run-id",
                "conflict",
                "--through",
                "prepare",
                "--execute-pipeline",
                "--resume",
                "--force",
            ]
        )
