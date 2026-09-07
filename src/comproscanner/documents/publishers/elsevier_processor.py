from comproscanner.documents.assets import xml_article_text
from comproscanner.documents.signals import match_property_signal

"""
elsevier_processor.py

Author: Aritra Roy
Email: contact@aritraroy.live
Website: https://aritraroy.live
Date: 23-02-2025"""
import os
import time
import re
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout
import pandas as pd
from dotenv import load_dotenv
from lxml import etree
from tqdm import tqdm
from comproscanner.documents.config import ArticlePaths
from comproscanner.documents.config import DefaultPaths
from comproscanner.documents.config import BaseUrls
from comproscanner.documents.config import ArticleRelatedKeywords
from comproscanner.documents.csv_store import ArticleCSVStore
from comproscanner._errors import ValueErrorHandler
from comproscanner._errors import KeyboardInterruptHandler
from comproscanner._logging import setup_logger
from comproscanner.documents.metadata import return_error_message
from comproscanner.documents.metadata import write_timeout_file
from comproscanner.documents.figures import FigureExtractor
from comproscanner.documents.figures import record_failed_article

load_dotenv()
logger = setup_logger("comproscanner.log", module_name="elsevier_processor")


class ElsevierArticleProcessor:
    """
    Get the article data from the XML response of the Elsevier API and process it to extract the required sections of the article and save it to the canonical Article CSV files.

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
        is_save_xml (bool): A flag to indicate if the XML response should be saved (default: False)
    """

    def __init__(
        self,
        main_property_keyword: str = None,
        property_keywords: dict = None,
        csv_batch_size: int = 1,
        start_row: int = None,
        end_row: int = None,
        doi_list: list = None,
        is_save_xml: bool = False,
        main_figure_keywords: dict = None,
        save_failed_automated_report: bool = True,
        failed_automated_report_path: str = None,
    ):
        keyword_message = return_error_message("main_property_keyword")
        property_keywords_message = return_error_message("property_keywords")
        api_key_message = return_error_message("scopus_api_key")
        self.keyword = main_property_keyword
        if self.keyword is None:
            logger.error(f"{keyword_message}")
            raise ValueErrorHandler(f"{keyword_message}")
        self.property_keywords = property_keywords
        if self.property_keywords is None:
            logger.error(f"{property_keywords_message}")
            raise ValueErrorHandler(f"{property_keywords_message}")
        self.api_key = os.getenv("SCOPUS_API_KEY")
        if self.api_key is None:
            logger.error(f"{api_key_message}")
            raise ValueErrorHandler(f"{api_key_message}")
        self.inst_token = os.getenv("SCIENCEDIRECT_INSTTOKEN")
        self.all_paths = DefaultPaths(self.keyword)
        self.article_paths = ArticlePaths(self.keyword)
        self.metadata_csv_filename = self.all_paths.METADATA_CSV_FILENAME
        self.csv_path = self.article_paths.EXTRACTED_CSV_FOLDERPATH
        self.csv_batch_size = csv_batch_size
        self.start_row = start_row
        self.end_row = end_row
        self.doi_list = doi_list
        self.is_save_xml = is_save_xml
        self.main_figure_keywords = (
            main_figure_keywords
            if main_figure_keywords is not None
            else property_keywords
        )
        self.timeout_file = self.all_paths.TIMEOUT_DOI_LOG_FILENAME
        self.article_related_keywords = ArticleRelatedKeywords()
        if self.inst_token is not None:
            self.headers = {
                "X-ELS-APIKey": self.api_key,
                "X-ELS-Insttoken": self.inst_token,
                "Accept": "application/xml",
            }
        else:
            self.headers = {"X-ELS-APIKey": self.api_key, "Accept": "application/xml"}
        self.df = None
        self.valid_property_articles = 0
        self.source = "elsevier"
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
        self.df = self.df[self.df["general_publisher"].str.lower() == "elsevier"]
        self.df = self.df.reset_index(drop=True)
        processed_dois = set()
        os.makedirs(self.csv_path, exist_ok=True)
        if os.path.exists(self.csv_filepath):
            try:
                df = pd.read_csv(self.csv_filepath, dtype=str, low_memory=False)
                processed_dois.update(df["doi"].tolist())
            except Exception as e:
                logger.warning(
                    f"Error reading CSV file: {e}. Processed DOIs from CSV will be ignored."
                )
        unprocessed_dois = set(self.df["doi"]) - processed_dois
        self.df = self.df[self.df["doi"].isin(unprocessed_dois)]

    def _parse_response(self, response):
        """
        Parse the XML response from the Elsevier API.

        Args:
            response (Response): Response object from the API call.

        Returns:
            root (Element): Root element of the parsed XML.
        """
        utf8_parser = etree.XMLParser(encoding="utf-8")
        try:
            root = etree.fromstring(response.text.encode("utf-8"), parser=utf8_parser)
            return root
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return None

    def _save_xml(self, response, doi):
        """
        Save the XML response to a file.

        Args:
            response (Response): Response object from the API call.
            doi (str): DOI of the article.
        """
        xml_folderpath = f"downloaded_files/xmls/elsevier"
        if not os.path.exists(xml_folderpath):
            os.makedirs(xml_folderpath)
        modified_doi = doi.replace("/", "_")
        with open(f"{xml_folderpath}/{modified_doi}.xml", "wb") as f:
            f.write(response.content)

    def _send_request(self, doi):
        """
        Send a request to the Elsevier API to get the article data.

        Args:
            doi (str): DOI of the article.

        Returns:
            response (Response): Response object from the API call, or "Not Found" if the article is not found, or None if there was an error.

        Raises:
            KeyboardInterruptHandler: If user interrupts the retry process

        Note:
            This method will retry indefinitely for connection errors until successful connection or KeyboardInterrupt
        """
        url = f"{BaseUrls.ELSEVIER_ARTICLE_BASE_URL}{doi}"
        retry_count = 0
        retry_delay = 60
        while True:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if retry_count > 0:
                    logger.info(
                        f"Connection restored successfully after {retry_count} attempts for DOI {doi}"
                    )
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    logger.critical(f"API rate limit exceeded for DOI: {doi}")
                    self.is_exceeded = True
                    return None
                elif response.status_code == 400:
                    logger.error(f"Bad request for DOI: {doi}")
                    return None
                elif response.status_code == 404:
                    logger.error(f"Article not found for DOI: {doi}")
                    return "Not Found"
                else:
                    logger.error(
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

    def _modify_specific_element(self, sections, element_name):
        """
        Modify specific elements in the XML response.

        Args:
            sections (Element): Element containing the sections of the article.
            element_name (str): Name of the element to modify.
        """

        def _get_text(elements):
            return "".join(
                (e.text.replace(" ", "") if e.text else "" for e in elements)
            ).rstrip()

        def _replace_element_with_text(element, text_to_add):
            parent = element.getparent()
            index = parent.index(element)
            if index > 0:
                target = parent[index - 1]
                target.tail = (
                    (target.tail or "") + text_to_add.lstrip() + (element.tail or "")
                )
            else:
                parent.text = (
                    (parent.text or "") + text_to_add.lstrip() + (element.tail or "")
                )
            parent.remove(element)

        for element in sections.xpath(f'//*[local-name()="{element_name}"]'):
            if element_name == "math":
                mn_elements = element.xpath('.//*[local-name()="mn"]')
                sup_elements = element.xpath('.//*[local-name()="msup"]')
                if mn_elements and sup_elements:
                    mn_text = "".join(
                        (
                            f"E^{{{e.text.strip()}}}" if e.text else ""
                            for e in mn_elements
                        )
                    )
                    other_text = _get_text(
                        [e for e in element.iter() if e not in mn_elements]
                    )
                    text_to_add = other_text + mn_text
                else:
                    text_to_add = _get_text(element.iter())
            elif element_name == "sup":
                text_to_add = f"E^{{{element.text}}}"
            _replace_element_with_text(element, text_to_add)

    def _modify_all_elements(self, filtered_sections):
        self._modify_specific_element(filtered_sections, "sup")
        self._modify_specific_element(filtered_sections, "math")
        return filtered_sections

    def _process_xml(self, root):
        """
        Process the XML response to extract the required sections of the article.

        Args:
            root (Element): Root element of the parsed XML.

        Returns:
            abstract (Element): Element containing the abstract of the article.
            modified_sections (list): List of elements containing the required sections of the article.
        """

        def _remove_elements(element_names, req_sections):
            for element_name in element_names:
                elements = req_sections.xpath(f'.//*[local-name()="{element_name}"]')
                if elements:
                    for element in elements:
                        parent = element.getparent()
                        index = parent.index(element)
                        if element.tail:
                            if index > 0:
                                preceding_sibling = parent[index - 1]
                                preceding_sibling.tail = (
                                    preceding_sibling.tail or ""
                                ) + element.tail
                            else:
                                parent.text = (parent.text or "") + element.tail
                        parent.remove(element)
            return req_sections

        abstract = root.xpath('.//*[local-name()="description"]')
        all_sections = root.xpath('.//*[local-name()="sections"]')
        req_sections = []
        modified_sections = []
        if all_sections:
            main_section = all_sections[0]
            main_section_elements = main_section.xpath('./*[local-name()="section"]')
            for section in main_section_elements:
                title_element = section.xpath(
                    './child::*[local-name()="section-title"]'
                )
                if title_element:
                    if title_element:
                        try:
                            title = title_element[0].text.lower()
                        except:
                            title = ""
                        if title:
                            if any(
                                (
                                    word in title.lower()
                                    for word_list in self.article_related_keywords.SECTION_TITLE_WORDS.values()
                                    for word in word_list
                                )
                            ):
                                req_sections.append(section)
        element_names = ["formula", "cross-ref", "cross-refs"]
        for section in req_sections:
            filtered_section = _remove_elements(element_names, section)
            modified_section = self._modify_all_elements(filtered_section)
            modified_sections.append(modified_section)
        if abstract:
            return (abstract, modified_sections)
        else:
            return (None, modified_sections)

    def _extract_and_save_figures(self, root, doi: str):
        """
        Save all available Elsevier XML figures; caption matches are diagnostic only.
        Downloads images from the Elsevier API and saves them to
        results/extracted_data/{keyword}/related_figures/{doi_}/{caption_id}.jpg
        alongside info.json.

        Args:
            root: lxml root element of the parsed Elsevier XML.
            doi (str): Article DOI.
        """
        base_path = f"results/extracted_data/{self.keyword}/related_figures"
        try:
            objects = root.xpath(
                './/*[local-name()="object"][@category="standard"][@type="IMAGE-DOWNSAMPLED"]'
            )
            ref_to_url = {}
            for obj in objects:
                ref = obj.get("ref")
                url = obj.text.strip() if obj.text else None
                if ref and url:
                    ref_to_url[ref] = url
            figures = root.xpath('.//*[local-name()="figure"]')
            logger.debug(
                f"Elsevier figure extraction for {doi}: found {len(figures)} figures and {len(ref_to_url)} image object mappings."
            )
            has_caption_keyword_match = False
            for figure_index, figure in enumerate(figures):
                caption_elements = figure.xpath(
                    './/*[local-name()="caption"]//*[local-name()="simple-para"]'
                )
                caption_text = " ".join(
                    ("".join(el.itertext()) for el in caption_elements)
                ).strip()
                if not caption_text:
                    caption_els = figure.xpath('.//*[local-name()="caption"]')
                    caption_text = " ".join(
                        ("".join(el.itertext()) for el in caption_els)
                    ).strip()
                main_match = FigureExtractor.keyword_matches_caption(
                    caption_text, self.main_figure_keywords
                )
                if main_match:
                    has_caption_keyword_match = True
                link_els = figure.xpath('.//*[local-name()="link"]')
                locator = None
                for link_el in link_els:
                    locator = link_el.get("locator")
                    if locator:
                        break
                if locator is None:
                    locator = figure.get("id", "unknown")
                caption_id = locator
                logger.debug(
                    f"Elsevier figure {figure_index} for {doi}: matched caption with locator='{locator}'."
                )
                FigureExtractor.update_info_json(
                    doi, caption_id, caption_text, base_path
                )
                url = ref_to_url.get(locator)
                if url:
                    logger.debug(
                        f"Elsevier figure {figure_index} for {doi}: resolved locator '{locator}' to URL '{url}'."
                    )
                    try:
                        img_headers = {
                            "X-ELS-APIKey": self.api_key,
                            "X-ELS-Insttoken": self.inst_token,
                            "Accept": "*/*",
                        }
                        resp = requests.get(url, headers=img_headers, timeout=30)
                        if resp.status_code == 200:
                            saved = FigureExtractor.save_figure_from_bytes(
                                resp.content, doi, caption_id, base_path
                            )
                            if saved:
                                logger.info(
                                    f"Saved Elsevier figure '{caption_id}' for {doi}"
                                )
                        else:
                            logger.warning(
                                f"Failed to download Elsevier figure '{caption_id}' for {doi}: HTTP {resp.status_code}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"Error downloading Elsevier figure '{caption_id}' for {doi}: {e}"
                        )
                else:
                    logger.warning(
                        f"No image URL found for Elsevier figure '{caption_id}' in {doi}. Available refs: {list(ref_to_url.keys())[:10]}"
                    )
            return has_caption_keyword_match
        except Exception as e:
            logger.warning(f"Error extracting figures from Elsevier XML for {doi}: {e}")
            return False

    def _extract_paragraphs(self, element):
        """
        Extract paragraphs from the sections of the article.

        Args:
            element (Element): Element containing the sections of the article.

        Returns:
            other_paragraphs (str): Paragraphs not containing the main property keyword.
            comp_paragraphs (str): Paragraphs containing the main property keyword.
        """
        paragraphs = element.xpath('.//*[local-name()="para"]')
        other_paragraphs = ""
        comp_paragraphs = ""
        for paragraph in paragraphs:
            paragraph_text = " " + "".join(paragraph.itertext())
            cleaned_text = re.sub(
                " \\.",
                ".",
                re.sub(
                    " \\[[,]*\\]| \\([,]*\\)", " ", re.sub("\\s+", " ", paragraph_text)
                ),
            )
            if any(
                (
                    word in cleaned_text
                    for word in self.article_related_keywords.COMP_KEYWORDS
                )
            ):
                comp_paragraphs += cleaned_text
            else:
                other_paragraphs += cleaned_text
        return (other_paragraphs, comp_paragraphs)

    def _append_sections_to_df(
        self,
        abstract,
        req_sections,
        doi,
        tables,
        article_title,
        publication_name,
        publisher,
        has_caption_keyword_match: bool = False,
    ):
        """
        Append the required sections to the dataframe.

        Args:
            abstract (Element): Element containing the abstract of the article.
            req_sections (list): List of elements containing the required sections of the article.
            doi (str): DOI of the article.
            tables (list): List of tables in the XML response.
            article_title (str): Title of the article.
            publication_name (str): Name of the publication.
            publisher (str): Name of the publisher.

        Returns:
            pd.DataFrame: Dataframe containing the extracted data for one article.
        """

        def _append_section(section):
            """
            Append the section to the dictionary of all paragraphs
            """
            other_section, comp_section = self._extract_paragraphs(section)
            encoded_other_section = other_section.encode("unicode_escape").decode(
                "utf-8"
            )
            encoded_comp_section = comp_section.encode("unicode_escape").decode("utf-8")
            return (encoded_other_section, encoded_comp_section)

        all_req_data = {
            "doi": doi,
            "article_title": article_title,
            "publication_name": publication_name,
            "publisher": publisher,
            "abstract": "",
            "introduction": "",
            "exp_methods": "",
            "comp_methods": "",
            "results_discussion": "",
            "conclusion": "",
            "is_property_mentioned": "0",
        }
        if abstract:
            try:
                abstract_text = " ".join(
                    (text.strip() for text in abstract[0].itertext() if text.strip())
                )
            except Exception:
                abstract_text = ""
            all_req_data["abstract"] = abstract_text
        for section in req_sections:
            title_element = section.xpath('./child::*[local-name()="section-title"]')
            if title_element:
                title = title_element[0].text.lower()
                if any(
                    (
                        word in title
                        for word in self.article_related_keywords.get_section_keywords(
                            "introduction"
                        )
                    )
                ):
                    other_section, comp_section = _append_section(section)
                    if other_section != "":
                        if "introduction" in all_req_data:
                            all_req_data["introduction"] += other_section
                        else:
                            all_req_data["introduction"] = other_section
                elif any(
                    (
                        word in title
                        for word in self.article_related_keywords.get_section_keywords(
                            "methods"
                        )
                    )
                ):
                    other_section, comp_section = _append_section(section)
                    if other_section != "":
                        if "exp_methods" in all_req_data:
                            all_req_data["exp_methods"] += other_section
                        else:
                            all_req_data["exp_methods"] = other_section
                    if comp_section != "":
                        if "comp_methods" in all_req_data:
                            all_req_data["comp_methods"] += comp_section
                        else:
                            all_req_data["comp_methods"] = comp_section
                elif any(
                    (
                        word in title
                        for word in self.article_related_keywords.get_section_keywords(
                            "results_discussion"
                        )
                    )
                ):
                    other_section, comp_section = _append_section(section)
                    whole_section = other_section + comp_section
                    if whole_section != "":
                        if "results_discussion" in all_req_data:
                            all_req_data["results_discussion"] += whole_section
                        else:
                            all_req_data["results_discussion"] = whole_section
                elif any(
                    (
                        word in title
                        for word in self.article_related_keywords.get_section_keywords(
                            "conclusion"
                        )
                    )
                ):
                    other_section, comp_section = _append_section(section)
                    if other_section != "":
                        if "conclusion" in all_req_data:
                            all_req_data["conclusion"] += other_section
                        else:
                            all_req_data["conclusion"] = other_section
        if tables:
            tables_content = "\n".join(tables)
            all_req_data["results_discussion"] += "\n" + tables_content
        total_text = f"#TITLE:\n{all_req_data['article_title']}\n\n# ABSTRACT:\n{all_req_data['abstract']}\n\n# INTRODUCTION:\n{all_req_data['introduction']}\n\n# EXPERIMENTAL SYNTHESIS:\n{all_req_data['exp_methods']}\n\n# COMPUTATIONAL METHODOLOGY:\n{all_req_data['comp_methods']}\n\n# RESULTS AND DISCUSSION:\n{all_req_data['results_discussion']}\n\n# CONCLUSION\n{all_req_data['conclusion']}"
        has_text_property_match = False
        if match_property_signal(total_text, self.property_keywords):
            has_text_property_match = True
            all_req_data["is_property_mentioned"] = "1"
        if has_caption_keyword_match and (not has_text_property_match):
            all_req_data["is_property_mentioned"] = "1"
        # Include sections with unfamiliar headings instead of silently losing them.
        all_req_data["full_text"] = "\n\n".join(
            [
                str(article_title or ""),
                str(all_req_data.get("abstract", "")),
                *(" ".join(section.itertext()) for section in req_sections),
                *(tables or []),
            ]
        )
        return pd.DataFrame([all_req_data])

    def _process_entries(self, entries):
        """
        Function to process and return the entries (body elements) of a table

        Args:
            entries (list): List of entries in a row of the table

        Returns:
            row_data (list): List of data in each row of the table
        """
        row_data = []
        for entry in entries:
            if entry.xpath('.//*[local-name()="sup"]'):
                self._modify_specific_element(entry, "sup")
            if entry.xpath('.//*[local-name()="math"]'):
                self._modify_specific_element(entry, "math")
            if entry.xpath('.//*[local-name()="br"]'):
                row_data.append(
                    [text.strip().replace("\\n", "") for text in entry.xpath("text()")]
                )
            else:
                text = " ".join(
                    "".join(entry.itertext())
                    .encode("unicode_escape")
                    .decode("utf-8")
                    .split()
                ).replace("\\n", "")
                row_data.append(text.strip().replace("\\n", ""))
        return row_data

    def _process_tables(self, tables):
        """
        Function to process and return the tables

        Args:
            tables (list): List of tables in the XML response

        Returns:
            header_data (list): List of headers of tables
            column_number (list): List of number of columns in each table
            all_table_data (list): List of data in each table
            caption_data (list): List of captions of each table
        """

        def _process_caption(caption_element):
            """Function to process and return the caption element of a table.

            Args:
                caption_element (Element): Element containing the caption of the table

            Returns:
                caption_data (str): Caption of the table
            """
            return (
                " ".join(
                    "".join(caption_element.itertext())
                    .encode("unicode_escape")
                    .decode("utf-8")
                    .split()
                )
                .strip()
                .replace("\\n", "")
            )

        def _process_header(head_element):
            """
            Function to process and return the header element of a table

            Args:
                head_element (Element): Element containing the header of the table

            Returns:
                header_data (list): List of headers of tables
            """
            if head_element.xpath('.//*[local-name()="sup"]'):
                self._modify_specific_element(head_element, "sup")
            if head_element.xpath('.//*[local-name()="math"]'):
                self._modify_specific_element(head_element, "math")
            return [
                " ".join(
                    "".join(entry.itertext())
                    .encode("unicode_escape")
                    .decode("utf-8")
                    .split()
                ).replace("\\n", "")
                for entry in head_element.xpath('.//*[local-name()="entry"]')
            ]

        def _process_rows(rows):
            """
            Function to process and return the rows of a table

            Args:
                rows (list): List of rows in the table

            Returns:
                all_row_data (list): List of data in each row of the table
            """
            all_row_data = []
            for row in rows:
                entries = row.xpath('.//*[local-name()="entry"]')
                all_row_data.append(self._process_entries(entries))
            return all_row_data

        header_data = []
        column_number = []
        all_table_data = []
        caption_data = []
        for table in tables:
            caption_elements = table.xpath('.//*[local-name()="caption"]')
            if caption_elements:
                caption_element = caption_elements[0]
                caption = _process_caption(caption_element)
                head_elements = table.xpath('.//*[local-name()="thead"]')
                if head_elements:
                    head_element = head_elements[0]
                    header = _process_header(head_element)
                    body_elements = table.xpath('.//*[local-name()="tbody"]')
                    if body_elements:
                        body_element = body_elements[0]
                        rows = _process_rows(
                            body_element.xpath('.//*[local-name()="row"]')
                        )
                        header_data.append(header)
                        column_number.append(len(header))
                        all_table_data.append(rows)
                        caption_data.append(caption)
        return (header_data, column_number, all_table_data, caption_data)

    def _generate_tables(
        self, header_data, column_number, all_table_data, caption_data
    ):
        """
        Function to generate markdown tables
        params: header_data: List of headers of tables
                column_number: List of number of columns in each table
                all_table_data: List of data in each table
        """
        tables = []
        if len(all_table_data) == len(header_data) == len(column_number):
            for i in range(len(all_table_data)):
                newline = "\n" if i == 0 else ""
                markdown_table = f"{newline}Table {i + 1}.{caption_data[i]}\n|{'|'.join(header_data[i])}|\n|{'|'.join(['---'] * column_number[i])}|\n"
                for row in all_table_data[i]:
                    row = [
                        str(item) if isinstance(item, list) else item for item in row
                    ]
                    markdown_table += "|" + "|".join(row) + "|\n"
                tables.append(markdown_table)
            return tables
        else:
            return "Error: Data mismatch"

    def _process_articles(self):
        """
        Main function to process the Elsevier articles and save the required sections to the canonical Article CSV files.
        """
        logger.debug(f"\nProcessing new articles...")
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
                    "API rate limit exceeded. Exiting the Elsevier processing..."
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
                            f"DOI {doi} for Elsevier article was not found in the metadata CSV."
                        )
                        continue
                    row = matching_rows.iloc[0]
                logger.debug(f"\n\nProcessing DOI: {row['doi']}")
                response = self._send_request(row["doi"])
                if response is None:
                    logger.warning(
                        f"Failed to download article...skipping {row['doi']}..."
                    )
                    self._record_failed_article(row["doi"], "download_failed")
                    continue
                if response == "Not Found":
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
                        if self.csv_batch_size > 1:
                            time.sleep(5)
                    continue
                root = self._parse_response(response)
                if root is None:
                    logger.error(f"Failed to parse XML...skipping {row['doi']}...")
                    self._record_failed_article(row["doi"], "xml_parse_failed")
                    continue
                original_full_text = xml_article_text(root)
                has_caption_keyword_match = self._extract_and_save_figures(
                    root, row["doi"]
                )
                if self.is_save_xml:
                    logger.info(f"Saving XML for DOI: {row['doi']}")
                    self._save_xml(response, row["doi"])
                tables = root.xpath('.//*[local-name()="table"]')
                if tables:
                    header_data, column_number, all_table_data, caption_data = (
                        self._process_tables(tables)
                    )
                    tables = self._generate_tables(
                        header_data, column_number, all_table_data, caption_data
                    )
                else:
                    tables = []
                abstract, sections = self._process_xml(root)
                row = self._append_sections_to_df(
                    abstract,
                    sections,
                    row["doi"],
                    tables,
                    row["article_title"],
                    row["publication_name"],
                    row["metadata_publisher"],
                    has_caption_keyword_match=has_caption_keyword_match,
                )
                row["full_text"] = original_full_text
                csv_dataframes.append(row)
                if row["is_property_mentioned"].iloc[0] == "1":
                    self.valid_property_articles += 1
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
                    if self.csv_batch_size > 1:
                        time.sleep(5)
                time.sleep(0.2)
            except KeyboardInterrupt as kie:
                logger.error(f"Keyboard Interruption Detected. {kie}. Exiting...")
                raise KeyboardInterruptHandler()
            except Exception as e:
                logger.error(
                    f"Error processing Elsevier article with DOI {row['doi']}: {e}"
                )
                continue
        if csv_dataframes:
            remaining_csv_df = pd.concat(csv_dataframes, ignore_index=True)
            self.article_store.write_to_csv(
                remaining_csv_df,
                self.csv_path,
                self.keyword,
                self.source,
                self.csv_batch_size,
            )

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

    def process_elsevier_articles(self):
        """Run Elsevier article processing workflow"""
        logger.verbose(f"\n\nElsevier articles processing started...\n\n")
        self._process_articles()
        self._process_with_timeout_handling()
        logger.verbose(f"\n\nElsevier articles processing completed...\n\n")
        logger.info(f"\nTotal valid property articles: {self.valid_property_articles}")
        if self.failed_automated_count > 0:
            logger.warning(
                f"Total failed Elsevier articles (download/parse): {self.failed_automated_count}"
            )
            if self.save_failed_automated_report:
                logger.info(
                    f"Failed automated report saved to: {self.failed_automated_report_path}"
                )
