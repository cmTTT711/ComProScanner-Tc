import json
import importlib

import pytest

from comproscanner.cli.main import main

cli_module = importlib.import_module("comproscanner.cli.main")


def test_process_articles_defaults_to_plan_only(tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("processing must not execute in plan mode")

    monkeypatch.setattr(cli_module, "execute_processing_plan", forbidden)
    assert main(
        ["process-articles", "--source", "manual_pdf", "--folder", str(tmp_path)]
    ) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["processor_sources"] == ["pdfs"]
    assert plan["metadata_network_allowed"] is False


def test_network_processing_requires_two_explicit_flags(monkeypatch):
    monkeypatch.setenv("SCOPUS_API_KEY", "present")
    with pytest.raises(SystemExit, match="require network access"):
        main(
            [
                "process-articles",
                "--source",
                "elsevier",
                "--execute-processing",
            ]
        )


def test_explicit_local_execution_uses_injected_cli_runner(tmp_path, monkeypatch):
    called = {}

    def fake_execute(plan, **kwargs):
        called["plan"] = plan
        called["kwargs"] = kwargs

    monkeypatch.setattr(cli_module, "execute_processing_plan", fake_execute)
    assert main(
        [
            "process-articles",
            "--source",
            "manual_pdf",
            "--folder",
            str(tmp_path),
            "--execute-processing",
        ]
    ) == 0
    assert called["plan"].processor_sources == ("pdfs",)
    assert called["kwargs"]["processing_kwargs"]["allow_missing_doi"] is True
