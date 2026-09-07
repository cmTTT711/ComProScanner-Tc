"""Same-number figures must keep independent caches, Facts, and Review sources."""

import json

import pandas as pd

from comproscanner.extraction.litellm_adapters import _LiteLLMClient
from comproscanner.cli.main import main


def test_same_figure_number_in_documents_survives_cli_and_review(tmp_path, monkeypatch):
    # These document identifiers become identical when path punctuation is
    # replaced by underscores. A document prefix alone would still collide.
    samples = [("paper/a", "BiFeO3", 1103), ("paper:a", "CoFe2O4", 793)]
    rows = []
    for index, (document_id, material, temperature) in enumerate(samples):
        folder = tmp_path / f"article_{index}"
        folder.mkdir()
        (folder / "figure_0.png").write_bytes(b"offline image fixture")
        manifest = folder / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "document_id": document_id,
                    "figures": [
                        {
                            "figure_id": "figure_0",
                            "path": "figure_0.png",
                            "caption": f"{material} has a Curie temperature of {temperature} K.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        rows.append(
            {
                "document_id": document_id,
                "full_text": "Article with a measured temperature-dependent figure.",
                "figures_manifest_path": str(manifest),
            }
        )
    source = tmp_path / "articles.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    calls = []

    def complete(_client, messages):
        calls.append(messages)
        content = messages[-1]["content"]
        if isinstance(content, list):
            # Exercise the actual image adapter but never contact a model.
            assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
            return content[0]["text"].split("ORIGINAL TEXT:\n", 1)[1]
        original = content.split("ORIGINAL EVIDENCE:\n", 1)[1]
        matches = [
            (material, value) for _, material, value in samples if material in original
        ]
        assert len(matches) == 1
        material, value = matches[0]
        return json.dumps(
            {
                "facts": [
                    {
                        "material_reported": material,
                        "value": value,
                        "unit": "K",
                    }
                ]
            }
        )

    monkeypatch.setattr(_LiteLLMClient, "complete", complete)
    outputs = tmp_path / "outputs"
    argv = [
        "run",
        "--processor-csv",
        str(source),
        "--provider",
        "figure",
        "--outputs",
        str(outputs),
        "--run-id",
        "figure-identity",
        "--vision-model",
        "offline-vision",
        "--through",
        "review",
        "--execute-pipeline",
        "--execute-models",
    ]
    assert main(argv) == 0
    run = outputs / "runs" / "figure-identity"
    evidence = json.loads((run / "evidence" / "all.json").read_text(encoding="utf-8"))
    assert len(evidence) == 2
    assert len({item["evidence_id"].casefold() for item in evidence}) == 2
    assert all(item["source_id"] == "figure_0" for item in evidence)
    cached = list((run / "papers").glob("*.json"))
    assert len(cached) == 2
    assert {path.stem for path in cached} == {item["evidence_id"] for item in evidence}
    predictions = json.loads((run / "predictions.json").read_text(encoding="utf-8"))
    assert {
        (fact["document_id"], fact["material_reported"]) for fact in predictions
    } == {(document_id, material) for document_id, material, _ in samples}
    review = pd.read_excel(run / "review.xlsx").set_index("document_id")
    for document_id, material, _ in samples:
        assert material in review.loc[document_id, "evidence"]
        other_material = next(
            other for other_doc, other, _ in samples if other_doc != document_id
        )
        assert other_material not in review.loc[document_id, "evidence"]
    assert len(calls) == 4  # One figure interpretation and extraction per source.
    # Force recovery from the individual paper caches, not predictions.json.
    (run / "predictions.json").unlink()
    assert (
        main(
            [
                "extract",
                "--outputs",
                str(outputs),
                "--run-id",
                "figure-identity",
                "--vision-model",
                "offline-vision",
                "--execute",
                "--resume",
            ]
        )
        == 0
    )
    assert len(calls) == 4
    assert (
        json.loads((run / "predictions.json").read_text(encoding="utf-8"))
        == predictions
    )
