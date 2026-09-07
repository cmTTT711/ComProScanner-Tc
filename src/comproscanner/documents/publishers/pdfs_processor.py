"""
pdfs_processor.py

Author: Aritra Roy
Email: contact@aritraroy.live
Website: https://aritraroy.live
Date: 21-03-2025"""

import logging
import time
import json
import pandas as pd
from tqdm import tqdm
import glob
import re
import os
import hashlib
from comproscanner.documents.config import ArticleRelatedKeywords
from comproscanner.documents.config import DefaultPaths
from comproscanner.documents.config import ArticlePaths
from comproscanner.documents.csv_store import ArticleCSVStore
from comproscanner._errors import ValueErrorHandler
from comproscanner._errors import KeyboardInterruptHandler
from comproscanner._logging import setup_logger
from comproscanner.documents.docling import PDFToMarkdownText
from comproscanner.documents.docling import sanitize_full_text
from comproscanner.documents.metadata import get_paper_metadata_from_openalex
from comproscanner.documents.metadata import get_doi_from_crossref
from comproscanner.documents.metadata import return_error_message

logger = setup_logger("comproscanner.log", module_name="pdfs_processor")


class PDFsProcessor:

    def __init__(
        self,
        folder_path: str = None,
        main_property_keyword: str = None,
        property_keywords: list = None,
        csv_batch_size: int = 1,
        save_failed_pdf_report: bool = True,
        failed_pdf_report_path: str = None,
        is_track_pdfs: bool = True,
        track_pdfs_report_path: str = None,
        allow_missing_doi: bool = False,
        allow_metadata_network: bool = True,
    ):
        """Class to process PDFs in a folder and process them to extract the required sections of the articles and save them to the canonical Article CSV files.

        Args:
            folder_path (str, required): Path to the folder containing PDFs.
            main_property_keyword (str: Required): The main keyword to process the articles for and file naming.
            property_keywords (dict: Required): A dictionary of property keywords which will be used for filtering sentences and should look like the following:
            {
                "exact_keywords": ["example1", "example2"],
                "substring_keywords": [" example 1 ", " example 2 "],
            }
            csv_batch_size (int): The number of rows to write to the CSV file at once (default: 1)
            is_track_pdfs (bool): Track processed DOIs in a txt file so re-runs skip already-processed PDFs (default: True)
            track_pdfs_report_path (str): Path to the DOI tracking txt file; defaults to <csv_path>/pdf_<keyword>_processed_dois.txt

        Raises:
            ValueErrorHandler: If the folder_path, main_property_keyword, or property_keywords is not provided.
        """
        self.folder_path = folder_path
        if self.folder_path == None:
            logger.error(f"PDF folder path cannot be empty. Exiting...")
            raise ValueErrorHandler(f"PDF folder path cannot be empty. Exiting...")
        keyword_message = return_error_message("main_property_keyword")
        property_keywords_message = return_error_message("property_keywords")
        self.keyword = main_property_keyword
        if self.keyword is None:
            logger.error(f"{keyword_message}")
            raise ValueErrorHandler(f"{keyword_message}")
        self.property_keywords = property_keywords
        if self.property_keywords is None:
            logger.error(f"{property_keywords_message}")
            raise ValueErrorHandler(f"{property_keywords_message}")
        self.save_failed_pdf_report = save_failed_pdf_report
        self.failed_pdf_report_path = failed_pdf_report_path or os.path.join(
            self.folder_path, "failed_pdf_filenames.txt"
        )
        self.failed_pdf_records = []
        self.is_track_pdfs = is_track_pdfs
        self.allow_missing_doi = allow_missing_doi
        self.allow_metadata_network = allow_metadata_network
        self.identifier = ""
        self.doi = ""
        self.all_paths = DefaultPaths(self.keyword)
        self.metadata_csv_filename = self.all_paths.METADATA_CSV_FILENAME
        self.article_paths = ArticlePaths(self.keyword)
        self.csv_path = self.article_paths.EXTRACTED_CSV_FOLDERPATH
        self.track_pdfs_report_path = (
            track_pdfs_report_path or self.all_paths.PDF_PROCESSED_DOIS_FILENAME
        )
        self.csv_batch_size = csv_batch_size
        self.timeout_file = self.all_paths.TIMEOUT_DOI_LOG_FILENAME
        self.article_keywords = ArticleRelatedKeywords()
        self.df = None
        self.valid_property_articles = 0
        self.source = "pdf"
        self.article_store = ArticleCSVStore()

    @staticmethod
    def _is_valid_doi(doi: str) -> bool:
        """Check whether a string is a valid DOI format."""
        if not doi:
            return False
        doi_pattern = "^10\\.\\d{4,9}/[-._;()/:a-zA-Z0-9]+$"
        return bool(re.match(doi_pattern, doi.strip()))

    def _filename_to_valid_doi(self, pdf_file: str) -> str:
        """Convert filename to DOI candidate and validate it."""
        filename = os.path.basename(pdf_file)
        candidate = filename.replace(".pdf", "").replace("_", "/").strip()
        return candidate if self._is_valid_doi(candidate) else ""

    @staticmethod
    def _local_document_id(pdf_file: str) -> str:
        """Return a stable internal identifier for a DOI-less local PDF."""
        filename = os.path.basename(pdf_file)
        digest = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:16]
        return f"local-pdf/{digest}"

    @staticmethod
    def _paper_id(pdf_file: str) -> str:
        match = re.match("^(\\d+)-", os.path.basename(pdf_file))
        return match.group(1) if match else ""

    @staticmethod
    def _file_hash(pdf_file: str) -> str:
        digest = hashlib.sha256()
        try:
            with open(pdf_file, "rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            return digest.hexdigest()
        except OSError:
            return ""

    def _record_failed_pdf(self, pdf_file: str, reason: str) -> None:
        """Record failed PDF filename cases and optionally write to report file."""
        filename = os.path.basename(pdf_file)
        entry = f"{filename}\t{reason}"
        self.failed_pdf_records.append(entry)
        logger.warning(f"Skipping {filename}: {reason}")
        if self.save_failed_pdf_report:
            try:
                with open(self.failed_pdf_report_path, "a", encoding="utf-8") as f:
                    f.write(entry + "\n")
            except Exception as e:
                logger.error(f"Error writing failed PDF report: {e}")

    def _extract_doi_from_text(self, text: str):
        """Extract DOI from text using regex pattern matching.

        Args:
            text (str): The text to extract DOI from.

        Returns:
            str: The extracted DOI or empty string if not found.
        """
        try:
            doi_pattern = "10\\.\\d{4,9}/[-._;()/:a-zA-Z0-9]+"
            matches = re.findall(doi_pattern, text)
            if matches:
                doi = matches[0].rstrip(".,;)]")
                logger.debug(f"DOI extracted: {doi}")
                return doi
            else:
                logger.debug("No DOI found in text")
                return ""
        except Exception as e:
            logger.error(f"Error extracting DOI from text: {e}")
            return ""

    def _create_empty_row(
        self, doi: str, title: str = "", journal_name: str = "", publisher: str = ""
    ):
        """Create a row with empty values for PDFs with no text detection.

        Args:
            doi (str): The DOI of the article (may be empty string).
            title (str): The title of the article.
            journal_name (str): The name of the publication.
            publisher (str): The name of the publisher.

        Returns:
            pd.DataFrame: DataFrame with metadata and empty section values and is_property_mentioned=0.
        """
        return pd.DataFrame(
            [
                {
                    "doi": doi,
                    "article_title": title,
                    "full_text": "",
                    "publication_name": journal_name,
                    "publisher": publisher,
                    "abstract": "",
                    "introduction": "",
                    "exp_methods": "",
                    "comp_methods": "",
                    "results_discussion": "",
                    "conclusion": "",
                    "is_property_mentioned": "0",
                    "paper_id": "",
                    "source_path": "",
                    "file_hash": "",
                }
            ]
        )

    def _is_corrupted_text(self, text: str) -> bool:
        """Check if the text contains corrupted GLYPH patterns from failed OCR.

        Args:
            text (str): The text to check.

        Returns:
            bool: True if text is corrupted (high ratio of GLYPH patterns), False otherwise.
        """
        if not text:
            return True
        glyph_pattern = "GLYPH(?:<|&lt;)\\d+(?:>|&gt;)"
        glyph_matches = re.findall(glyph_pattern, text)
        glyph_count = len(glyph_matches)
        words = text.split()
        word_count = len(words)
        if word_count == 0:
            return True
        glyph_ratio = glyph_count / word_count
        return glyph_ratio > 0.1

    def _load_processed_pdfs(self) -> tuple:
        """Return (processed_filenames, processed_dois) from the tracking file or CSV fallback.

        Tracking file format: one ``basename<TAB>doi`` entry per line.
        The filename set enables a pre-conversion skip; the DOI set handles the
        CSV fallback path (where no filename mapping is available).
        """
        filenames, dois = (set(), set())
        if self.is_track_pdfs and os.path.exists(self.track_pdfs_report_path):
            try:
                with open(self.track_pdfs_report_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("\t", 1)
                        if len(parts) == 2:
                            filenames.add(parts[0])
                            if parts[1]:
                                dois.add(parts[1])
                        elif len(parts) == 1 and parts[0]:
                            dois.add(parts[0])
                logger.debug(
                    f"Loaded {len(filenames)} processed filename(s) and {len(dois)} DOI(s) from tracking file."
                )
                return (filenames, dois)
            except Exception as e:
                logger.warning(
                    f"Could not read tracking file, falling back to CSV: {e}"
                )
        output_file = f"{self.csv_path}/pdf_{self.keyword}_paragraphs.csv"
        if os.path.exists(output_file):
            try:
                existing_df = pd.read_csv(output_file, dtype=str, usecols=["doi"])
                dois = set(existing_df["doi"].dropna().str.strip())
            except Exception as e:
                logger.warning(f"Could not load processed DOIs from CSV: {e}")
        return (filenames, dois)

    def _mark_pdf_processed(self, pdf_file: str, doi: str) -> None:
        """Append a ``basename<TAB>doi`` entry to the tracking file."""
        if not self.is_track_pdfs:
            return
        try:
            parent = os.path.dirname(self.track_pdfs_report_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.track_pdfs_report_path, "a", encoding="utf-8") as f:
                f.write(f"{os.path.basename(pdf_file)}\t{doi}\n")
        except Exception as e:
            logger.warning(f"Could not write to tracking file: {e}")

    def _get_metadata_from_csv(self, doi: str):
        """Try to get metadata from the local metadata CSV file.

        Args:
            doi (str): The DOI to search for.

        Returns:
            tuple: (title, journal_name, publisher) or ("", "", "") if not found.
        """
        try:
            if not os.path.exists(self.metadata_csv_filename):
                return ("", "", "")
            if self.df is None:
                self.df = pd.read_csv(self.metadata_csv_filename)
            matching_rows = self.df[self.df["doi"] == doi]
            if not matching_rows.empty:
                row = matching_rows.iloc[0]
                title = row.get("article_title", "")
                journal_name = row.get("publication_name", "")
                publisher = row.get("metadata_publisher", "")
                return (title, journal_name, publisher)
            return ("", "", "")
        except Exception as e:
            logger.warning(f"Error reading metadata from CSV: {e}")
            return ("", "", "")

    def process_pdfs(self):
        """
        Main function to process the PDFs in the folder. It reads the PDFs, extracts the text, and writes the data to CSV file, to the SQL database (if set), and creates a vector database if the keyword is found in the text.
        """
        csv_dataframes = []
        pdf_files = glob.glob(f"{self.folder_path}/*.pdf")
        total_files = len(pdf_files)
        processed_filenames, processed_dois = self._load_processed_pdfs()
        skipped_count = 0
        logger.verbose(f"\n\nParsing of PDFs started...")
        logger.debug(f"\nTotal PDF files found: {total_files}")
        if processed_filenames or processed_dois:
            logger.info(
                f"Tracking file loaded: {len(processed_filenames)} filename(s) and {len(processed_dois)} DOI(s) — matching PDFs will be skipped."
            )
        for pdf_file in tqdm(
            pdf_files, desc="Processing PDFs", total=total_files, colour="#d6adff"
        ):
            try:
                if os.path.basename(pdf_file) in processed_filenames:
                    skipped_count += 1
                    logger.debug(
                        f"Skipping already-processed PDF: {os.path.basename(pdf_file)}"
                    )
                    continue
                pdf_to_md = PDFToMarkdownText(source=pdf_file)
                md_text = pdf_to_md.convert_to_markdown()
                if (
                    md_text is None
                    or not md_text.strip()
                    or self._is_corrupted_text(md_text)
                ):
                    logger.warning(
                        f"Text detection result is empty or corrupted for {pdf_file}. Storing with is_property_mentioned=0 and skipping vector database creation."
                    )
                    filename = os.path.basename(pdf_file)
                    self.doi = self._filename_to_valid_doi(pdf_file)
                    self.identifier = filename.replace(".pdf", "")
                    if not self.doi:
                        if self.allow_missing_doi:
                            self.doi = self._local_document_id(pdf_file)
                        else:
                            self._record_failed_pdf(
                                pdf_file,
                                "empty_or_corrupted_text_and_filename_not_valid_doi",
                            )
                            continue
                    title, journal_name, publisher = ("", "", "")
                    if self.allow_metadata_network and self.doi.startswith("10."):
                        title, journal_name, publisher = (
                            get_paper_metadata_from_openalex(self.doi)
                        )
                        if not title or not journal_name or (not publisher):
                            csv_title, csv_journal, csv_publisher = (
                                self._get_metadata_from_csv(self.doi)
                            )
                            title = title or csv_title
                            journal_name = journal_name or csv_journal
                            publisher = publisher or csv_publisher
                    row = self._create_empty_row(
                        self.doi, title, journal_name, publisher
                    )
                    row["paper_id"] = self._paper_id(pdf_file)
                    row["source_path"] = os.path.abspath(pdf_file)
                    row["file_hash"] = self._file_hash(pdf_file)
                    row["parser_manifest_path"] = getattr(
                        pdf_to_md, "assets_manifest", ""
                    )
                    csv_dataframes.append(row)
                    if len(csv_dataframes) == self.csv_batch_size:
                        final_csv_df = pd.concat(csv_dataframes, ignore_index=True)
                        self.article_store.write_to_csv(
                            final_csv_df,
                            self.csv_path,
                            self.keyword,
                            self.source,
                            self.csv_batch_size,
                        )
                        csv_dataframes = []
                        time.sleep(5)
                    self._mark_pdf_processed(pdf_file, self.doi)
                    continue
                self.doi = self._extract_doi_from_text(md_text)
                if self.doi:
                    self.identifier = self.doi
                    logger.debug(f"DOI found: {self.doi}")
                else:
                    crossref_doi = (
                        get_doi_from_crossref(md_text)
                        if self.allow_metadata_network
                        else ""
                    )
                    if crossref_doi:
                        self.doi = crossref_doi
                        self.identifier = crossref_doi
                        logger.info(
                            f"DOI resolved via CrossRef for {pdf_file}: {self.doi}"
                        )
                    else:
                        filename = os.path.basename(pdf_file)
                        self.identifier = filename.replace(".pdf", "")
                        self.doi = self._filename_to_valid_doi(pdf_file)
                        if not self.doi:
                            if self.allow_missing_doi:
                                self.doi = self._local_document_id(pdf_file)
                                logger.info(
                                    "DOI not found for %s; using internal document id %s",
                                    pdf_file,
                                    self.doi,
                                )
                            else:
                                self._record_failed_pdf(
                                    pdf_file, "doi_not_found_and_filename_not_valid_doi"
                                )
                                continue
                        if self._is_valid_doi(self.doi):
                            logger.warning(
                                f"DOI not found in text/CrossRef for {pdf_file}. Using filename-derived DOI: {self.doi}"
                            )
                if self.doi and self.doi in processed_dois:
                    skipped_count += 1
                    logger.debug(
                        f"Skipping already-processed PDF (DOI match): {os.path.basename(pdf_file)}"
                    )
                    continue
                title, journal_name, publisher = ("", "", "")
                if self.allow_metadata_network and self._is_valid_doi(self.doi):
                    title, journal_name, publisher = get_paper_metadata_from_openalex(
                        self.doi
                    )
                    if not title or not journal_name or (not publisher):
                        csv_title, csv_journal, csv_publisher = (
                            self._get_metadata_from_csv(self.doi)
                        )
                        title = title or csv_title
                        journal_name = journal_name or csv_journal
                        publisher = publisher or csv_publisher
                    if not title:
                        logger.warning(f"Metadata not found for DOI: {self.doi}")
                has_caption_keyword_match = pdf_to_md.extract_and_save_figures(
                    self.doi,
                    None,
                    base_path=f"results/extracted_data/{self.keyword}/related_figures",
                )
                title = title or getattr(pdf_to_md, "parsed_title", "")
                all_sections = pdf_to_md.clean_text(md_text)
                row = pdf_to_md.append_section_to_df(
                    all_sections,
                    self.doi,
                    title,
                    journal_name,
                    publisher,
                    self.property_keywords,
                    logger,
                    has_caption_keyword_match=has_caption_keyword_match,
                )
                row["full_text"] = sanitize_full_text(md_text)
                row["paper_id"] = self._paper_id(pdf_file)
                row["source_path"] = os.path.abspath(pdf_file)
                row["file_hash"] = self._file_hash(pdf_file)
                row["parser_manifest_path"] = getattr(pdf_to_md, "assets_manifest", "")
                csv_dataframes.append(row)
                if row["is_property_mentioned"].iloc[0] == "1":
                    self.valid_property_articles += 1
                self._mark_pdf_processed(pdf_file, self.doi)
                if len(csv_dataframes) == self.csv_batch_size:
                    final_csv_df = pd.concat(csv_dataframes, ignore_index=True)
                    self.article_store.write_to_csv(
                        final_csv_df,
                        self.csv_path,
                        self.keyword,
                        self.source,
                        self.csv_batch_size,
                    )
                    csv_dataframes = []
                    time.sleep(5)
                time.sleep(0.2)
            except KeyboardInterrupt as kie:
                logger.error(f"Keyboard Interruption Detected. {kie}")
                raise KeyboardInterruptHandler()
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                continue
        try:
            if csv_dataframes:
                remaining_csv_df = pd.concat(csv_dataframes, ignore_index=True)
                self.article_store.write_to_csv(
                    remaining_csv_df, self.csv_path, self.keyword, self.source
                )
        except Exception as e:
            logger.error(f"Error writing remaining dataframes: {e}")
        logger.verbose(f"\n\nParsing of PDFs completed...")
        logger.info(f"\nTotal valid property articles: {self.valid_property_articles}")
        if skipped_count:
            logger.info(f"Skipped {skipped_count} already-processed PDF(s).")
        if self.failed_pdf_records:
            logger.warning(
                f"Total skipped PDFs due to invalid filename DOI fallback: {len(self.failed_pdf_records)}"
            )
            if self.save_failed_pdf_report:
                logger.info(
                    f"Failed PDF report saved to: {self.failed_pdf_report_path}"
                )
