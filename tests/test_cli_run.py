import json

import pandas as pd
import pytest

from comproscanner.cli.main import main


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
            ["run", "--csv", str(tmp_path / "missing.csv"),
             "--run-id", "blocked", "--execute-pipeline"]
        )
    assert not (tmp_path / "outputs").exists()


def test_run_can_normalize_and_prepare_locally_without_models(tmp_path):
    source = tmp_path / "processor.csv"
    pd.DataFrame(
        [{
            "doi": "10.1/test", "article_title": "BFO",
            "abstract": "BiFeO3 has a Curie temperature of 1103 K.",
            "introduction": "", "exp_methods": "", "comp_methods": "",
            "results_discussion": "", "conclusion": "",
            "is_property_mentioned": "1",
        }]
    ).to_csv(source, index=False)
    outputs = tmp_path / "outputs"
    assert main(
        ["run", "--processor-csv", str(source), "--run-id", "local",
         "--outputs", str(outputs), "--through", "prepare",
         "--execute-pipeline"]
    ) == 0
    run = outputs / "runs" / "local"
    assert (run / "article.csv").is_file()
    assert (run / "evidence" / "all.json").is_file()
    assert not (run / "predictions.json").exists()


def test_extract_material_parser_requires_explicit_network_permission():
    with pytest.raises(SystemExit, match="requires --execute-network"):
        main(
            ["extract", "--run-id", "x", "--execute",
             "--material-normalizer", "material-parser-api"]
        )
