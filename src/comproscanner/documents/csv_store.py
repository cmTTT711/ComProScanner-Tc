"""Canonical Article CSV persistence; no SQL or model dependencies."""

import io
import os
import json
from pathlib import Path
import pandas as pd
from comproscanner.documents.schemas import (
    normalize_legacy_article_frame,
    validate_article_frame,
)
from comproscanner._logging import setup_logger

logger = setup_logger("comproscanner.log", module_name="article_csv")


def read_csv_sanitizing_nul(file_path):
    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        csv_text = file.read().replace("\x00", "")
    return pd.read_csv(io.StringIO(csv_text), dtype=str)


class ArticleCSVStore:
    """Manages writing article extraction results to CSV files."""

    def __init__(self):
        pass

    def write_to_csv(self, final_df, filepath, keyword, source, csv_batch_size):
        """Write the DataFrame to a CSV file, appending new rows and skipping duplicate DOIs.

        Args:
            final_df (pd.DataFrame): DataFrame containing article data to write.
            filepath (str): Directory path where the CSV file will be created.
            keyword (str): Property keyword used to construct the output filename.
            source (str): Publisher/source label used to construct the output filename.
            csv_batch_size (int): Batch size; values greater than 1 trigger an info log.
        """
        if csv_batch_size > 1:
            logger.info("Writing to CSV...")
        try:
            final_df = normalize_legacy_article_frame(final_df, source_type=source)
            for row_index, row in final_df.iterrows():
                if str(row.get("figures_manifest_path", "")).strip():
                    continue
                document_id = str(row["document_id"])
                figure_folder = document_id.replace("/", "_").replace(":", "_")
                manifest = (
                    Path(filepath) / "related_figures" / figure_folder / "manifest.json"
                )
                if manifest.is_file():
                    final_df.at[row_index, "figures_manifest_path"] = str(manifest)
                    try:
                        payload = json.loads(manifest.read_text(encoding="utf-8"))
                        final_df.at[row_index, "figure_count"] = str(
                            len(payload.get("figures", []))
                        )
                    except (OSError, json.JSONDecodeError):
                        pass
            validate_article_frame(final_df)
            import hashlib

            for _, article in final_df.iterrows():
                directory = (
                    Path(filepath)
                    / "articles"
                    / hashlib.sha256(str(article["document_id"]).encode()).hexdigest()[
                        :16
                    ]
                )
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "article.md").write_text(
                    str(article["full_text"]), encoding="utf-8"
                )
                (directory / "metadata.json").write_text(
                    json.dumps(
                        {
                            key: str(value)
                            for key, value in article.items()
                            if key
                            not in {
                                "full_text",
                                "abstract",
                                "introduction",
                                "exp_methods",
                                "comp_methods",
                                "results_discussion",
                                "conclusion",
                                "tables",
                            }
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

            if not os.path.exists(filepath):
                os.makedirs(filepath)

            output_file = f"{filepath}/{source}_{keyword}_paragraphs.csv"

            if os.path.exists(output_file):
                # Read all columns as strings to avoid mixed type issues
                existing_df = normalize_legacy_article_frame(
                    pd.read_csv(output_file, dtype=str), source_type=source
                )
                final_df = final_df[~final_df["doi"].isin(existing_df["doi"])]
                if not final_df.empty:
                    combined_df = pd.concat([existing_df, final_df], ignore_index=True)
                    combined_df.to_csv(output_file, index=False)
            else:
                final_df.to_csv(output_file, index=False)

        except Exception as e:
            logger.error(f"Error: {e}")
            raise
