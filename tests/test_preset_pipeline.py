"""Acceptance of a second property through the real CLI, with no paid calls."""

import json
from pathlib import Path

import pandas as pd
import pytest
import requests

from comproscanner.extraction.litellm_adapters import _LiteLLMClient
from comproscanner.cli.main import main
from comproscanner.results.facts import MaterialParserAPINormalizer


def _fact(material, method):
    return {
        "material_reported": material,
        "property": "band gap",
        "value": 3.2,
        "unit": "eV",
        "conditions": {"determination_method": method},
    }


def _inputs(tmp_path):
    source = tmp_path / "articles.csv"
    pd.DataFrame(
        [
            {
                "document_id": "sample-zno",
                "full_text": (
                    "The optical band gap of ZnO is 3.2 eV. The computed electronic "
                    "band gap of ZnO is also 3.2 eV."
                ),
                "is_property_mentioned": "0",
            },
            {
                "document_id": "sample-tio2",
                "full_text": "TiO2 has an optical band gap of 3.2 eV.",
                "is_property_mentioned": "0",
            },
        ]
    ).to_csv(source, index=False)
    gold = tmp_path / "gold.json"
    gold.write_text(
        json.dumps(
            [
                {
                    "document_id": document,
                    "property": "band gap",
                    "material": material,
                    "value": "3.2",
                    "unit": "eV",
                    "conditions": {"determination_method": method},
                }
                for document, material, method in (
                    ("sample-zno", "ZnO", "optical"),
                    ("sample-zno", "ZnO", "computational"),
                    ("sample-tio2", "TiO2", "optical"),
                )
            ]
        ),
        encoding="utf-8",
    )
    return source, gold


def _fake_models(monkeypatch, *, malformed=False):
    calls = []

    def complete(client, messages):
        calls.append((client.settings, messages))
        prompt = messages[-1]["content"]
        if messages[0]["content"].startswith("You identify"):
            assert "band-gap" in prompt
            return '{"answer":"yes"}'
        original = prompt.split("ORIGINAL EVIDENCE:\n", 1)[1]
        # Each call sees exactly one source. Preset examples are not evidence.
        if "ZnO" in original:
            assert "TiO2" not in original
            facts = [_fact("ZnO", "optical"), _fact("ZnO", "computational")]
        else:
            assert "TiO2" in original and "ZnO" not in original
            facts = [_fact("TiO2", "optical")]
        if malformed:
            facts.extend(
                [
                    None,
                    {"value": 7},
                    {**facts[0], "conditions": ["wrong"]},
                    {**facts[0], "qualifier": ["approximately"]},
                ]
            )
        return json.dumps({"facts": facts})

    monkeypatch.setattr(_LiteLLMClient, "complete", complete)
    return calls


def _argv(tmp_path, source, gold, through="evaluate"):
    return [
        "run",
        "--processor-csv",
        str(source),
        "--preset",
        "band_gap",
        "--provider",
        "rule_text",
        "--outputs",
        str(tmp_path / "outputs"),
        "--run-id",
        "band-gap",
        "--through",
        through,
        "--gold",
        str(gold),
        "--execute-pipeline",
        "--execute-models",
    ]


def test_second_preset_runs_article_to_review_and_evaluation(tmp_path, monkeypatch):
    source, gold = _inputs(tmp_path)
    calls = _fake_models(monkeypatch)
    secret = "test-secret-not-for-output"
    monkeypatch.setenv("DASHSCOPE_API_KEY", secret)
    argv = _argv(tmp_path, source, gold)
    assert main(argv) == 0
    run = tmp_path / "outputs" / "runs" / "band-gap"
    predictions = json.loads((run / "predictions.json").read_text(encoding="utf-8"))
    evidence = json.loads((run / "evidence" / "all.json").read_text(encoding="utf-8"))
    assert len(evidence) == 2  # Legacy article flags never gate extraction.
    assert len(calls) == 4  # Identifier + extractor independently per Evidence.
    assert len(predictions) == 3  # Same value, different methods stay separate.
    assert all(item["property_name"] == "band gap" for item in predictions)
    assert all(
        item["evidence_ids"] and not item["processing_issues"] for item in predictions
    )
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    assert (metrics["tp"], metrics["fp"], metrics["fn"]) == (3, 0, 0)
    review = pd.read_excel(run / "review.xlsx")
    assert len(review) == 3 and review["evidence"].notna().all()
    assert "processing_issues" in review.columns
    config_text = (run / "run_config.json").read_text(encoding="utf-8")
    config = json.loads(config_text)["extraction"]
    assert config["models"]["identifier"]["api_key_env"] == "DASHSCOPE_API_KEY"
    assert secret not in config_text
    assert main([*argv, "--resume"]) == 0
    assert len(calls) == 4
    with pytest.raises(ValueError, match="settings or Evidence changed"):
        main([*argv, "--resume", "--extractor-model", "another-model"])
    assert len(calls) == 4


def test_failed_material_service_keeps_facts_and_review_diagnostics(
    tmp_path, monkeypatch
):
    source, gold = _inputs(tmp_path)
    _fake_models(monkeypatch)

    def unavailable(self, material):
        response = requests.Response()
        response.status_code = 503
        raise requests.HTTPError(response=response)

    monkeypatch.setattr(MaterialParserAPINormalizer, "_resolve_http", unavailable)
    assert (
        main(
            [
                *_argv(tmp_path, source, gold, through="review"),
                "--material-normalizer",
                "material-parser-api",
                "--execute-network",
            ]
        )
        == 0
    )
    run = tmp_path / "outputs" / "runs" / "band-gap"
    predictions = json.loads((run / "predictions.json").read_text(encoding="utf-8"))
    assert len(predictions) == 3
    assert all(
        item["material_reported"] == item["material_normalized"] for item in predictions
    )
    assert all(
        "HTTP 503" in " ".join(item["processing_issues"]) for item in predictions
    )
    review = pd.read_excel(run / "review.xlsx")
    assert review["processing_issues"].str.contains("HTTP 503").all()
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    assert summary["facts_needing_review"] == 3


def test_invalid_model_rows_are_recorded_without_losing_valid_siblings(
    tmp_path, monkeypatch
):
    source, gold = _inputs(tmp_path)
    _fake_models(monkeypatch, malformed=True)
    argv = _argv(tmp_path, source, gold, through="review")
    assert main(argv) == 1
    run = tmp_path / "outputs" / "runs" / "band-gap"
    predictions = json.loads((run / "predictions.json").read_text(encoding="utf-8"))
    failures = json.loads((run / "failures.json").read_text(encoding="utf-8"))
    assert len(predictions) == 3 and len(failures) == 8
    assert all("raw_fact" in item and "evidence_id" in item for item in failures)
    assert (run / "review.xlsx").is_file()
    assert main([*argv, "--resume"]) == 1


def test_extract_rejects_preset_mismatch_before_model_calls(tmp_path, monkeypatch):
    source, gold = _inputs(tmp_path)
    calls = _fake_models(monkeypatch)
    assert main(_argv(tmp_path, source, gold, through="review")) == 0
    with pytest.raises(ValueError, match="different property preset"):
        main(
            [
                "extract",
                "--run-id",
                "band-gap",
                "--outputs",
                str(tmp_path / "outputs"),
                "--preset",
                "curie_temperature",
                "--execute",
                "--resume",
            ]
        )
    assert len(calls) == 4


@pytest.mark.parametrize("change", ["input", "provider", "chunking"])
def test_resume_rejects_changed_preparation_before_model_calls(
    tmp_path, monkeypatch, change
):
    source, gold = _inputs(tmp_path)
    calls = _fake_models(monkeypatch)
    argv = _argv(tmp_path, source, gold, through="review")
    assert main(argv) == 0
    additions = []
    if change == "input":
        source.write_text(
            source.read_text(encoding="utf-8").replace("3.2", "4.2"), encoding="utf-8"
        )
    elif change == "provider":
        additions = ["--provider", "table"]
    else:
        additions = ["--target-words", "180"]
    with pytest.raises(ValueError, match="Preparation settings or input changed"):
        main([*argv, "--resume", *additions])
    assert len(calls) == 4


def test_historical_id_mismatch_is_not_reported_as_zero_accuracy(tmp_path, monkeypatch):
    source, gold = _inputs(tmp_path)
    _fake_models(monkeypatch)
    assert main(_argv(tmp_path, source, gold, through="review")) == 0
    gold.write_text(
        json.dumps(
            [{"paper_id": 1, "material": "ZnO", "tc_value": "3.2", "tc_unit": "eV"}]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="document IDs do not overlap"):
        main(
            [
                "evaluate",
                "--run-id",
                "band-gap",
                "--outputs",
                str(tmp_path / "outputs"),
                "--gold",
                str(gold),
            ]
        )
