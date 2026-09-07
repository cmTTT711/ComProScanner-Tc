from comproscanner.documents.signals import (
    sanitize_full_text,
    match_property_signal,
    matches_property_keywords,
)

"""
pdf_to_markdown_text.py

Author: Aritra Roy
Email: contact@aritraroy.live
Website: https://aritraroy.live
Date: 21-03-2025
"""
import re
import os
import time
import unicodedata
from io import BytesIO
import pandas as pd
import torch
import requests
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
)
from docling.datamodel.settings import settings
from docling_core.types.doc import PictureItem, TableItem
from requests.exceptions import Timeout, RequestException
from comproscanner._errors import ValueErrorHandler
from comproscanner._errors import KeyboardInterruptHandler
from comproscanner.documents.config import ArticleRelatedKeywords
from comproscanner._logging import setup_logger
from comproscanner.documents.figures import FigureExtractor

logger = setup_logger("comproscanner.log", module_name="pdf_to_markdown_text")
IMAGE_RESOLUTION_SCALE = 2.0


class PDFToMarkdownText:

    def __init__(self, source: str = None, num_threads: int = 4):
        """Class to convert PDF to Markdown text.

        Args:
            source (str, required): Source PDF file path or URL. Defaults to None.
            num_threads (int, optional): Number of CPU threads to use for conversion. Defaults to 4.
        """
        self.source = source
        if self.source == None:
            logger.error("Source cannot be empty...")
            raise ValueErrorHandler(f"Source cannot be empty...")
        self.article_keywords = ArticleRelatedKeywords()
        self.num_threads = num_threads
        self.converter = self._setup_converter()
        self._document = None

    @staticmethod
    def _stringify_caption_value(value) -> str:
        """Convert a Docling caption-like value into plain text."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (list, tuple)):
            text_parts = [
                PDFToMarkdownText._stringify_caption_value(item)
                for item in value
                if item is not None
            ]
            return " ".join((part for part in text_parts if part)).strip()
        if hasattr(value, "itertext"):
            try:
                return " ".join(
                    (text.strip() for text in value.itertext() if text.strip())
                )
            except Exception:
                pass
        for attr in ("text", "orig", "content", "label"):
            attr_value = getattr(value, attr, None)
            if isinstance(attr_value, str) and attr_value.strip():
                return attr_value.strip()
        return str(value).strip()

    def _extract_caption_text(self, element) -> str:
        """Extract caption text from a Docling picture/table item with fallbacks."""
        caption_candidates = []
        try:
            caption_from_method = element.caption_text(self._document)
            if caption_from_method:
                caption_candidates.append(caption_from_method)
        except Exception:
            pass
        for attr_name in ("captions", "caption", "caption_data"):
            attr_value = getattr(element, attr_name, None)
            if attr_value:
                caption_candidates.append(self._stringify_caption_value(attr_value))
        for candidate in caption_candidates:
            normalized = re.sub("\\s+", " ", candidate).strip()
            if normalized:
                return normalized
        return ""

    def _setup_converter(self):
        """Setup document converter with appropriate acceleration options.

        Returns:
            DocumentConverter: Configured document converter
        """
        try:
            if torch.cuda.is_available():
                device = AcceleratorDevice.CUDA
                logger.info("Using CUDA acceleration for PDF processing")
            else:
                device = AcceleratorDevice.CPU
                logger.info("No GPU available, using CPU for PDF processing")
        except ImportError:
            device = AcceleratorDevice.CPU
            logger.info("PyTorch not available, using CPU for PDF processing")
        accelerator_options = AcceleratorOptions(
            num_threads=self.num_threads, device=device
        )
        pipeline_options = PdfPipelineOptions()
        pipeline_options.accelerator_options = accelerator_options
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        pipeline_options.generate_table_images = True
        settings.debug.profile_pipeline_timings = True
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        return converter

    def convert_to_markdown(self):
        """Parse once; report failures to the document stage without endless retries."""
        try:
            result = self.converter.convert(self.source)
            self._document = result.document
            markdown = result.document.export_to_markdown()
            from comproscanner.documents.assets import (
                save_document_assets,
                document_title,
            )

            self.parsed_title = document_title(self._document)
            self.assets_manifest = save_document_assets(
                self._document, markdown, self.source
            )
            return markdown
        except KeyboardInterrupt:
            raise KeyboardInterruptHandler()
        except Exception as exc:
            logger.error("PDF conversion failed for %s: %s", self.source, exc)
            return None

    def extract_and_save_figures(
        self, doi: str, main_figure_keywords: dict = None, base_path: str = None
    ):
        """
        Extract figures/tables from converted PDF using Docling item images and save them.
        If main_figure_keywords is provided, only figures whose captions match are saved;
        if None, all figures are saved.

        Must be called after convert_to_markdown() so that self._document is populated.

        Args:
            doi (str): Article DOI.
            main_figure_keywords (dict, optional): Dict with "exact_keywords" and/or
                "substring_keywords". If None, all figures are saved.
            base_path (str, optional): Base directory for saving figures. Defaults to
                FigureExtractor.BASE_PATH ("results/related_figures").
        """
        if self._document is None:
            logger.warning(
                "extract_and_save_figures called before convert_to_markdown(); skipping."
            )
            return False
        try:
            match_counter = 0
            has_caption_keyword_match = False
            for element, _level in self._document.iterate_items():
                if not isinstance(element, (PictureItem, TableItem)):
                    continue
                caption_text = self._extract_caption_text(element)
                if main_figure_keywords and (
                    not FigureExtractor.keyword_matches_caption(
                        caption_text, main_figure_keywords
                    )
                ):
                    continue
                has_caption_keyword_match = True
                caption_id = f"figure_{match_counter}"
                FigureExtractor.update_info_json(
                    doi, caption_id, caption_text, base_path
                )
                try:
                    image = element.get_image(self._document)
                except Exception as e:
                    logger.warning(
                        f"Could not render image for figure '{caption_id}' in {doi}: {e}"
                    )
                    match_counter += 1
                    continue
                if image is None:
                    logger.warning(
                        f"Docling returned empty image for figure '{caption_id}' in {doi}"
                    )
                    match_counter += 1
                    continue
                try:
                    image_bytes_buffer = BytesIO()
                    image.save(image_bytes_buffer, format="PNG")
                    saved = FigureExtractor.save_figure_from_bytes(
                        image_bytes_buffer.getvalue(), doi, caption_id, base_path
                    )
                    if saved:
                        logger.info(f"Saved figure '{caption_id}' for {doi} -> {saved}")
                except Exception as e:
                    logger.warning(
                        f"Failed to save rendered image for figure '{caption_id}' in {doi}: {e}"
                    )
                match_counter += 1
            return has_caption_keyword_match
        except Exception as e:
            logger.warning(f"Error extracting figures from PDF for {doi}: {e}")
            return False

    @staticmethod
    def clean_text(text: str):
        """Function to clean the text.

        Args:
            text (str, required): Text to be cleaned.

        Returns:
            str: Cleaned text.
        """

        def _split_at_references(text: str):
            pattern = "\\n(?:#{1,3})\\s*.*?references.*$"
            parts = re.split(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            return parts[0] if parts else text

        def _split_into_sections(text: str):
            """
            Function to split the text into sections based on the section headers.

            Args:
                text (str, required): Text to be split into sections.

            Returns:
                list: List of sections.
            """
            pattern = "\\n(?=#{1,3}\\s)"
            sections = re.split(pattern, text)
            return [section.strip() for section in sections if section.strip()]

        md_text = text.replace("<!-- image -->", "")
        md_text = _split_at_references(md_text)
        sections = _split_into_sections(md_text)
        return sections

    def append_section_to_df(
        self,
        req_sections,
        doi,
        article_title,
        publication_name,
        publisher,
        property_keywords,
        logger,
        has_caption_keyword_match: bool = False,
    ):
        """
        Function to append the sections to the dataframe.

        Args:
            req_sections (list): List of sections.
            doi (str): DOI of the article.
            article_title (str): Title of the article.
            publication_name (str): Name of the publication.
            publisher (str): Name of the publisher.
            property_keywords (dict): Dict of property keywords with "exact_keywords" and/or "substring_keywords".
            vector_db_manager (VectorDatabaseManager): Manager used to create/check vector databases for relevant articles.
            logger (logging.Logger): Logger object.
            has_caption_keyword_match (bool, optional): Whether a figure caption matched a property keyword. Defaults to False.

        Returns:
            pd.DataFrame: Dataframe containing the article data.
        """
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

        def _get_diff_paragraphs(section: str):
            """
            Function to separate the paragraphs containing the computational keywords from the other paragraphs.
            Args:
                section (str, required): Section text.

            Returns:
                comp_paragraphs (str): Computational paragraphs.
                other_paragraphs (str): Other paragraphs.
            """
            other_paragraphs = ""
            comp_paragraphs = ""
            paragraphs = section.split("\n\n")
            for paragraph in paragraphs:
                if any(
                    (
                        keyword in paragraph.lower()
                        for keyword in self.article_keywords.COMP_KEYWORDS
                    )
                ):
                    comp_paragraphs += paragraph
                else:
                    other_paragraphs += paragraph
            return (other_paragraphs, comp_paragraphs)

        def _get_section_type(section_title: str, keywords_dict: dict):
            """
            Function to determine the type of section based on its title and a list of keywords

            Args:
                section_title (str, required): Title of the section.
                keywords_dict (dict, required): Dict of keywords to search for.

            Returns:
                index (int/None): Section index if found, else None
            """
            section_title_lower = section_title.lower()
            for section_type, keywords in keywords_dict.items():
                for keyword in keywords:
                    if any((keyword in word for word in section_title_lower.split())):
                        return section_type
            return None

        def _fetch_abstract_from_semantic_scholar(doi_value: str) -> str:
            """
            Try fetching abstract via Semantic Scholar Graph API (no API key).
            """
            if not doi_value or not doi_value.startswith("10."):
                return ""
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi_value}?fields=abstract"
            headers = {"Accept": "application/json"}
            try:
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code != 200:
                    logger.warning(
                        f"Semantic Scholar abstract fetch failed for {doi_value}: HTTP {response.status_code}"
                    )
                    return ""
                payload = response.json()
                abstract = payload.get("abstract", "")
                return abstract.strip() if isinstance(abstract, str) else ""
            except Exception as e:
                logger.warning(
                    f"Semantic Scholar abstract fetch error for {doi_value}: {e}"
                )
                return ""

        def _fallback_abstract_from_pre_intro(
            sections: list, title_value: str = ""
        ) -> str:
            """
            Build abstract fallback from all section text before introduction,
            after removing title text.
            """
            pre_intro_chunks = []
            for section in sections:
                section_lines = section.split("\n")
                first_line = section_lines[0] if section_lines else ""
                modified_first_line = first_line.lower().replace(" ", "")
                section_type = _get_section_type(
                    modified_first_line, self.article_keywords.SECTION_TITLE_WORDS
                )
                if section_type == "introduction":
                    break
                section_content = "\n".join(
                    (line.strip() for line in section_lines[1:] if line.strip())
                ).strip()
                if section_content:
                    pre_intro_chunks.append(section_content)
            abstract_fallback = "\n".join(pre_intro_chunks).strip()
            if title_value:
                abstract_fallback = abstract_fallback.replace(title_value, "").strip()
            return abstract_fallback

        def _combine_sections(sections: list, section_keywords: dict):
            """Classify and merge raw section texts into the canonical section buckets.

            Args:
                sections (list): List of section text strings (header + body).
                section_keywords (dict): Mapping of section type → list of header keywords.

            Returns:
                dict: Keys are canonical section names (abstract, introduction,
                      experimental_methods, computational_methods, results_discussion,
                      conclusion); values are concatenated section text strings.
            """
            final_sections = {
                "abstract": "",
                "introduction": "",
                "experimental_methods": "",
                "computational_methods": "",
                "results_discussion": "",
                "conclusion": "",
            }
            current_section_type = None
            for section in sections:
                section_lines = section.split("\n")
                first_line = section_lines[0]
                modified_first_line = first_line.lower().replace(" ", "")
                section_content = "\n".join(
                    (line.strip() for line in section_lines[1:] if line.strip())
                )
                section_type = _get_section_type(modified_first_line, section_keywords)
                if section_type:
                    current_section_type = section_type
                if current_section_type:
                    other_content, comp_content = _get_diff_paragraphs(section_content)
                    if current_section_type == "methods":
                        if other_content:
                            if final_sections["experimental_methods"]:
                                final_sections["experimental_methods"] += (
                                    "\n" + other_content
                                )
                            else:
                                final_sections["experimental_methods"] = other_content
                        if comp_content:
                            if final_sections["computational_methods"]:
                                final_sections["computational_methods"] += (
                                    "\n" + comp_content
                                )
                            else:
                                final_sections["computational_methods"] = comp_content
                    elif current_section_type == "results_discussion":
                        content_to_add = other_content
                        if comp_content:
                            if content_to_add:
                                content_to_add += "\n" + comp_content
                            else:
                                content_to_add = comp_content
                        if content_to_add:
                            if final_sections["results_discussion"]:
                                final_sections["results_discussion"] += (
                                    "\n" + content_to_add
                                )
                            else:
                                final_sections["results_discussion"] = content_to_add
                    elif other_content:
                        if final_sections[current_section_type]:
                            final_sections[current_section_type] += "\n" + other_content
                        else:
                            final_sections[current_section_type] = other_content
            return final_sections

        final_sections = _combine_sections(
            req_sections, self.article_keywords.SECTION_TITLE_WORDS
        )
        all_req_data["abstract"] = final_sections["abstract"]
        all_req_data["introduction"] = final_sections["introduction"]
        all_req_data["exp_methods"] = final_sections["experimental_methods"]
        all_req_data["comp_methods"] = final_sections["computational_methods"]
        all_req_data["results_discussion"] = final_sections["results_discussion"]
        all_req_data["conclusion"] = final_sections["conclusion"]
        if not all_req_data["abstract"].strip():
            semantic_abstract = _fetch_abstract_from_semantic_scholar(doi)
            if semantic_abstract:
                logger.info(
                    f"Abstract recovered from Semantic Scholar API for DOI: {doi}"
                )
                all_req_data["abstract"] = semantic_abstract
            else:
                pre_intro_abstract = _fallback_abstract_from_pre_intro(
                    req_sections, article_title
                )
                if pre_intro_abstract:
                    logger.info(
                        f"Abstract recovered from pre-introduction text for DOI: {doi}"
                    )
                    all_req_data["abstract"] = pre_intro_abstract
        total_text = f"#TITLE:\n{all_req_data['article_title']}\n\n# ABSTRACT:\n{all_req_data['abstract']}\n\n# INTRODUCTION:\n{all_req_data['introduction']}\n\n# EXPERIMENTAL SYNTHESIS:\n{all_req_data['exp_methods']}\n\n# COMPUTATIONAL METHODOLOGY:\n{all_req_data['comp_methods']}\n\n# RESULTS AND DISCUSSION:\n{all_req_data['results_discussion']}\n\n# CONCLUSION\n{all_req_data['conclusion']}"
        has_text_property_match = matches_property_keywords(
            total_text, property_keywords
        )
        if has_text_property_match:
            all_req_data["is_property_mentioned"] = "1"
            modified_doi = doi.replace("/", "_")
        if has_caption_keyword_match and (not has_text_property_match):
            all_req_data["is_property_mentioned"] = "1"
            modified_doi = doi.replace("/", "_")
        return pd.DataFrame([all_req_data])
