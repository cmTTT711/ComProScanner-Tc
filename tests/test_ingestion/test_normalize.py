import pandas as pd

from comproscanner.ingestion import normalize_article_csvs


def test_normalize_merges_and_deduplicates_legacy_csvs(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    pd.DataFrame(
        [{"doi": "10.1/a", "article_title": "A", "results_discussion": "Tc 400 K"}]
    ).to_csv(first, index=False)
    pd.DataFrame(
        [
            {"doi": "10.1/a", "article_title": "duplicate"},
            {"doi": "10.1/b", "article_title": "B"},
        ]
    ).to_csv(second, index=False)
    output = normalize_article_csvs([first, second], tmp_path / "canonical.csv")
    result = pd.read_csv(output)
    assert list(result["document_id"]) == ["10.1/a", "10.1/b"]
    assert set(["schema_version", "source_type", "source_path"]).issubset(result.columns)


def test_normalize_resolves_relative_figure_manifest_from_processor_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "processor.csv"
    pd.DataFrame([{
        "doi": "10.1/a",
        "article_title": "A",
        "figures_manifest_path": "figures/paper-a.json",
    }]).to_csv(source, index=False)
    output = normalize_article_csvs(
        [source], tmp_path / "canonical.csv", source_root=workspace
    )
    result = pd.read_csv(output)
    assert result.loc[0, "figures_manifest_path"] == str(
        (workspace / "figures" / "paper-a.json").resolve()
    )
