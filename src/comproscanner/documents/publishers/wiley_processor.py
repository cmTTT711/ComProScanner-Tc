import json

"\nwiley_processor.py\n\nAuthor: Aritra Roy\nEmail: contact@aritraroy.live\nWebsite: https://aritraroy.live\nDate: 28-03-2025"
import os
import sys
import time
import tempfile
import re
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from comproscanner.documents.config import ArticleRelatedKeywords
from comproscanner.documents.config import DefaultPaths
from comproscanner.documents.config import ArticlePaths
from comproscanner.documents.config import BaseUrls
from comproscanner.documents.csv_store import ArticleCSVStore
from comproscanner._errors import ValueErrorHandler
from comproscanner._errors import KeyboardInterruptHandler
from comproscanner._logging import setup_logger
from comproscanner.documents.docling import PDFToMarkdownText, sanitize_full_text
from comproscanner.documents.metadata import get_paper_metadata_from_openalex
from comproscanner.documents.metadata import return_error_message
from comproscanner.documents.metadata import write_timeout_file
from comproscanner.documents.figures import record_failed_article

load_dotenv()
logger = setup_logger("comproscanner.log", module_name="wiley_processor")


class WileyArticleProcessor:
    """
    Get the article as PDF using Wiley API and process it to extract the required sections of the article and save it to the canonical Article CSV files.

    Args:
        main_property_keyword (str: Required): The main keyword to process the articles for and file naming
        property_keywords (dict: Required): A dictionary of property keywords which will be used for filtering sentences and should look like the following:
        {
            "exact_keywords": ["example1", "example2"],
            "substring_keywords": [" example 1 ", " example 2 "],
        }
        csv_batch_size (int): The number of rows to write to the CSV file at once (default: 1)
        start_row (int): The row number to start processing from (default: None)
        end_row (int): The row number to end processing at (default: None)
        doi_list (list): A list of DOIs to process (default: None)
    """

    def __init__(
        self,
        main_property_keyword: str = None,
        property_keywords: dict = None,
        csv_batch_size: int = 1,
        start_row: int = None,
        end_row: int = None,
        doi_list: list = None,
        is_save_pdf: bool = False,
        save_failed_automated_report: bool = True,
        failed_automated_report_path: str = None,
    ):
        keyword_message = return_error_message("main_property_keyword")
        property_keywords_message = return_error_message("property_keywords")
        api_key_message = return_error_message("wiley_api_key")
        self.keyword = main_property_keyword
        if self.keyword is None:
            logger.error(f"{keyword_message}")
            raise ValueErrorHandler(f"{keyword_message}")
        self.property_keywords = property_keywords
        if self.property_keywords is None:
            logger.error(f"{property_keywords_message}")
            raise ValueErrorHandler(f"{property_keywords_message}")
        self.api_key = os.getenv("WILEY_API_KEY")
        if self.api_key is None:
            logger.error(f"{api_key_message}")
            raise ValueErrorHandler(f"{api_key_message}")
        self.all_paths = DefaultPaths(self.keyword)
        self.article_paths = ArticlePaths(self.keyword)
        self.metadata_csv_filename = self.all_paths.METADATA_CSV_FILENAME
        self.csv_path = self.article_paths.EXTRACTED_CSV_FOLDERPATH
        self.csv_batch_size = csv_batch_size
        self.start_row = start_row
        self.end_row = end_row
        self.doi_list = doi_list
        self.is_save_pdf = is_save_pdf
        self.timeout_file = self.all_paths.TIMEOUT_DOI_LOG_FILENAME
        self.article_related_keywords = ArticleRelatedKeywords()
        self.headers = {"X-ELS-APIKey": self.api_key, "Accept": "application/xml"}
        self.df = None
        self.valid_property_articles = 0
        self.source = "wiley"
        self.csv_filepath = (
            f"{self.csv_path}/{self.source}_{self.keyword}_paragraphs.csv"
        )
        self.save_failed_automated_report = save_failed_automated_report
        self.failed_automated_report_path = (
            failed_automated_report_path
            or self.all_paths.FAILED_AUTOMATED_ARTICLES_FILENAME
        )
        self.failed_automated_count = 0
        self.article_store = ArticleCSVStore()
        self.is_exceeded = False

    def _record_failed_article(self, doi: str, reason: str) -> None:
        """Record a failed article to the automated failure report."""
        self.failed_automated_count += 1
        record_failed_article(
            doi,
            self.source,
            reason,
            self.failed_automated_report_path,
            self.save_failed_automated_report,
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

    def _load_and_preprocess_data(self):
        """
        Load and preprocess the metadata CSV file to get the DOIs of the articles to process.
        """
        self.df = pd.read_csv(self.metadata_csv_filename)
        self.df = self.df.dropna(subset=["doi"])
        if self.start_row is not None and self.end_row is not None:
            self.df = self.df.iloc[self.start_row : self.end_row]
        elif self.start_row is not None:
            self.df = self.df.iloc[self.start_row :]
        elif self.end_row is not None:
            self.df = self.df.iloc[: self.end_row]
        self.df = self.df[self.df["general_publisher"].str.lower() == "wiley"]
        self.df = self.df.reset_index(drop=True)
        processed_dois = set()
        os.makedirs(self.csv_path, exist_ok=True)
        if os.path.exists(self.csv_filepath):
            try:
                df = pd.read_csv(self.csv_filepath)
                processed_dois.update(df["doi"].tolist())
            except Exception as e:
                logger.warning(
                    f"Error reading CSV file: {e}. Processed DOIs from CSV will be ignored."
                )
        unprocessed_dois = set(self.df["doi"]) - processed_dois
        self.df = self.df[self.df["doi"].isin(unprocessed_dois)]

    def _send_request(self, doi):
        """
        Send a GET request to the Wiley API to get the article as PDF.

        Args:
            doi (str: Required): The DOI of the article.

        Returns:
            tmp_path (str): The path of the temporary PDF file, or "Not Found" if the article is not found, or None if there was an error.

        Raises:
            KeyboardInterruptHandler: If user interrupts the retry process

        Note:
            This method will retry indefinitely for connection errors until successful connection or KeyboardInterrupt
        """
        retry_delay = 60
        retry_count = 0
        url = f"{BaseUrls.WILEY_ARTICLE_BASE_URL}{doi}"
        headers = {"Wiley-TDM-Client-Token": os.getenv("WILEY_API_KEY")}
        while True:
            try:
                if retry_count > 0:
                    logger.info(
                        f"Connection restored successfully after {retry_count} attempts for DOI {doi}"
                    )
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    if self.is_save_pdf:
                        filepath = self._save_pdf(doi, response)
                        return filepath
                    else:
                        with tempfile.NamedTemporaryFile(
                            suffix=".pdf", delete=False
                        ) as tmp_file:
                            tmp_file.write(response.content)
                            tmp_file.flush()
                            tmp_path = tmp_file.name
                            return tmp_path
                elif response.status_code == 429:
                    logger.critical(
                        f"API rate limit exceeded. Please try again later. DOI: {doi}"
                    )
                    self.is_exceeded = True
                    return None
                elif response.status_code == 400:
                    logger.error(f"Bad request for DOI: {doi}")
                    return None
                elif response.status_code == 404:
                    logger.warning(f"Article not found for DOI: {doi}")
                    return "Not Found"
                else:
                    logger.warning(
                        f"Request failed with status code {response.status_code} for DOI: {doi}"
                    )
                    return None
            except (ConnectionError, Timeout) as e:
                retry_count += 1
                logger.warning(
                    f"Connection error occurred while fetching DOI {doi}: {type(e).__name__}: {str(e)}"
                )
                logger.info(
                    f"Retrying in {retry_delay} seconds... (Attempt #{retry_count})"
                )
                logger.info(
                    f"Waiting for connection to restore. Press Ctrl+C to cancel."
                )
                try:
                    time.sleep(retry_delay)
                except KeyboardInterrupt:
                    logger.warning("User interrupted the retry process.")
                    raise KeyboardInterruptHandler()
            except requests.exceptions.ReadTimeout as e:
                retry_count += 1
                logger.warning(f"Read timeout error for DOI: {doi}")
                logger.info(
                    f"Retrying in {retry_delay} seconds... (Attempt #{retry_count})"
                )
                logger.info(
                    f"Waiting for connection to restore. Press Ctrl+C to cancel."
                )
                write_timeout_file(doi, self.timeout_file)
                try:
                    time.sleep(retry_delay)
                except KeyboardInterrupt:
                    logger.warning("User interrupted the retry process.")
                    raise KeyboardInterruptHandler()
            except RequestException as e:
                retry_count += 1
                if hasattr(e, "response") and e.response is not None:
                    response = e.response
                    if response.status_code == 429:
                        logger.critical(f"API rate limit exceeded for DOI: {doi}")
                        self.is_exceeded = True
                        return None
                    elif response.status_code == 400:
                        logger.error(f"Bad request for DOI: {doi}")
                        return None
                    elif response.status_code == 404:
                        logger.warning(f"Article not found for DOI: {doi}")
                        return None
                    else:
                        logger.warning(
                            f"Request failed with status code {response.status_code} for DOI: {doi}"
                        )
                        logger.info(
                            f"Retrying in {retry_delay} seconds... (Attempt #{retry_count})"
                        )
                        try:
                            time.sleep(retry_delay)
                        except KeyboardInterrupt:
                            logger.warning("User interrupted the retry process.")
                            raise KeyboardInterruptHandler()
                else:
                    logger.error(
                        f"Request exception occurred while fetching DOI {doi}: {type(e).__name__}: {str(e)}"
                    )
                    logger.info(
                        f"Retrying in {retry_delay} seconds... (Attempt #{retry_count})"
                    )
                    try:
                        time.sleep(retry_delay)
                    except KeyboardInterrupt:
                        logger.warning("User interrupted the retry process.")
                        raise KeyboardInterruptHandler()
            except KeyboardInterrupt:
                logger.warning("User interrupted the connection attempt.")
                raise KeyboardInterruptHandler()
            except Exception as e:
                logger.error(
                    f"Unexpected error for DOI {doi}: {type(e).__name__}: {str(e)}"
                )
                return None

    def _save_pdf(self, doi, response):
        """
        Save the PDF file to the local disk.

        Args:
            doi (str: Required): The DOI of the article.
            response (requests.Response: Required): The response object from the GET request.
        """
        pdf_folderpath = f"downloaded_files/pdfs/wiley"
        if not os.path.exists(pdf_folderpath):
            os.makedirs(pdf_folderpath)
        modified_doi = doi.replace("/", "_")
        filepath = f"{pdf_folderpath}/{modified_doi}.pdf"
        with open(f"{filepath}", "wb") as f:
            f.write(response.content)
        return filepath

    def _process_articles(self):
        """
        Main function to process the Wiley articles and save the required sections to the canonical Article CSV files.
        """
        logger.debug(f"\nProcessing articles for the first time...")
        self._load_and_preprocess_data()
        csv_dataframes = []
        if self.doi_list is None:
            iterable = self.df.iterrows()
            total = self.df.shape[0]
        else:
            iterable = enumerate(self.doi_list)
            total = len(self.doi_list)
        for _, item in tqdm(iterable, total=total, colour="#d6adff"):
            if self.is_exceeded:
                logger.critical(
                    "API rate limit exceeded. Exiting the Wiley processing..."
                )
                break
            try:
                doi = None
                if self.doi_list is None:
                    row = item
                    doi = row["doi"]
                else:
                    doi = item
                    self.df = pd.read_csv(self.metadata_csv_filename)
                    matching_rows = self.df[self.df["doi"] == doi]
                    if matching_rows.empty:
                        logger.warning(
                            f"DOI {doi} for Wiley article was not found in the metadata CSV."
                        )
                        continue
                    row = matching_rows.iloc[0]
                logger.debug(f"\n\nProcessing Wiley article DOI: {row['doi']}")
                file_path = self._send_request(row["doi"])
                if file_path is None or file_path == "Not Found":
                    if file_path is None:
                        logger.warning(
                            f"Failed to download PDF for DOI {row['doi']}. Storing with is_property_mentioned=0."
                        )
                        self._record_failed_article(row["doi"], "download_failed")
                    else:
                        logger.warning(
                            f"Article not found for DOI {row['doi']}. Storing with is_property_mentioned=0."
                        )
                        self._record_failed_article(row["doi"], "not_found")
                    empty_data = {
                        "doi": row["doi"],
                        "article_title": row["article_title"],
                        "publication_name": row["publication_name"],
                        "publisher": row["metadata_publisher"],
                        "abstract": "",
                        "introduction": "",
                        "exp_methods": "",
                        "comp_methods": "",
                        "results_discussion": "",
                        "conclusion": "",
                        "is_property_mentioned": "0",
                    }
                    empty_row = pd.DataFrame([empty_data])
                    csv_dataframes.append(empty_row)
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
                    continue
                title = row.get("article_title", "")
                journal_name = row.get("publication_name", "")
                publisher = row.get("metadata_publisher", "")
                pdf_to_md = PDFToMarkdownText(file_path)
                md_text = pdf_to_md.convert_to_markdown()
                if (
                    md_text is None
                    or not md_text.strip()
                    or self._is_corrupted_text(md_text)
                ):
                    logger.warning(
                        f"Text detection result is empty or corrupted for DOI {doi}. Storing with is_property_mentioned=0 and skipping vector database creation."
                    )
                    self._record_failed_article(doi, "pdf_text_extraction_failed")
                    if not self.is_save_pdf and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            logger.warning(
                                f"Failed to remove temp file {file_path}: {e}"
                            )
                    empty_data = {
                        "doi": doi,
                        "article_title": title,
                        "publication_name": journal_name,
                        "publisher": publisher,
                        "abstract": "",
                        "introduction": "",
                        "exp_methods": "",
                        "comp_methods": "",
                        "results_discussion": "",
                        "conclusion": "",
                        "is_property_mentioned": "0",
                    }
                    empty_row = pd.DataFrame([empty_data])
                    csv_dataframes.append(empty_row)
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
                    continue
                has_caption_keyword_match = pdf_to_md.extract_and_save_figures(
                    row["doi"],
                    None,
                    base_path=f"results/extracted_data/{self.keyword}/related_figures",
                )
                title = title or getattr(pdf_to_md, "parsed_title", "")
                all_sections = pdf_to_md.clean_text(md_text)
                row = pdf_to_md.append_section_to_df(
                    all_sections,
                    row["doi"],
                    title,
                    journal_name,
                    publisher,
                    self.property_keywords,
                    logger,
                    has_caption_keyword_match=has_caption_keyword_match,
                )
                row["parser_manifest_path"] = getattr(pdf_to_md, "assets_manifest", "")
                row["full_text"] = sanitize_full_text(md_text)
                row["source_path"] = os.path.abspath(file_path)
                csv_dataframes.append(row)
                if row["is_property_mentioned"].iloc[0] == "1":
                    self.valid_property_articles += 1
                if not self.is_save_pdf and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove temp file {file_path}: {e}")
                if len(csv_dataframes) == self.csv_batch_size:
                    final_df = pd.concat(csv_dataframes, ignore_index=True)
                    self.article_store.write_to_csv(
                        final_df,
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
                logger.error(f"Error processing article with DOI {row['doi']}: {e}")
                continue
        try:
            if csv_dataframes:
                remaining_csv_df = pd.concat(csv_dataframes, ignore_index=True)
                self.article_store.write_to_csv(
                    remaining_csv_df, self.csv_path, self.keyword, self.source
                )
        except Exception as e:
            logger.error(f"Error writing remaining dataframes: {e}")

    def _process_with_timeout_handling(self):
        """Process articles and handle any timeouts"""
        while os.path.isfile(self.timeout_file):
            logger.debug(f"\nProcessing articles with timeout handling...")
            with open(self.timeout_file, "r") as file:
                timeout_dois = [line.strip() for line in file]
            if not timeout_dois:
                break
            self.doi_list = timeout_dois
            if self.doi_list:
                self._process_articles()
                if os.path.exists(self.timeout_file):
                    os.remove(self.timeout_file)

    def process_wiley_articles(self):
        """Run Wiley article processing workflow"""
        logger.verbose(f"\n\nWiley articles processing started...")
        self._process_articles()
        self._process_with_timeout_handling()
        logger.verbose(f"\n\nWiley articles processing completed...")
        logger.info(f"\nTotal valid property articles: {self.valid_property_articles}")
        if self.failed_automated_count > 0:
            logger.warning(
                f"Total failed Wiley articles (download/parse): {self.failed_automated_count}"
            )
            if self.save_failed_automated_report:
                logger.info(
                    f"Failed automated report saved to: {self.failed_automated_report_path}"
                )
