"""Route acquisition to the existing source processors, producing only Articles."""

import os
from typing import Optional, Dict
from comproscanner._errors import ValueErrorHandler
from comproscanner._logging import setup_logger

logger = setup_logger("comproscanner.log", module_name="document_dispatch")


class ArticleProcessor:

    def __init__(self, main_property_keyword):
        self.main_property_keyword = main_property_keyword

    def process_articles(
        self,
        property_keywords: dict = None,
        source_list: Optional[list] = None,
        folder_path: str = None,
        csv_batch_size: int = 1,
        start_row: int = None,
        end_row: int = None,
        doi_list: list = None,
        is_save_xml: bool = False,
        is_save_pdf: bool = False,
        main_figure_keywords: Optional[Dict] = None,
        save_failed_pdf_report: bool = True,
        failed_pdf_report_path: Optional[str] = None,
        save_failed_automated_report: bool = True,
        failed_automated_report_path: Optional[str] = None,
        allow_missing_doi: bool = False,
        allow_metadata_network: bool = True,
    ):
        """Process articles for the main property keyword.

        Args:
            property_keywords (dict, required): A dictionary of property keywords which will be used for filtering sentences and should look like the following::

                {
                    "exact_keywords": ["example1", "example2"],
                    "substring_keywords": [" example 1 ", " example 2 "],
                }
            source_list (list, optional): List of sources to process the articles from. Defaults to ["elsevier", "wiley", "iop", "springer"] - currently supported publishers.
            folder_path (str, optional): Path to the folder containing PDFs. Defaults to None.
            csv_batch_size (int, optional): The number of rows to write to the CSV file at once. Defaults to 1.
            start_row (int, optional): Start row to process the articles from. Defaults to None.
            end_row (int, optional): End row to process the articles to. Defaults to None.
            doi_list (list, optional): List of DOIs to process the articles for. Defaults to None.
            is_save_xml (bool, optional): A flag to indicate if the XML files should be saved. Defaults to False.
            is_save_pdf (bool, optional): A flag to indicate if the PDF files should be saved. Defaults to False.
            main_figure_keywords (dict, optional): Keywords to match figure captions for figure extraction. Same format as property_keywords with "exact_keywords" and "substring_keywords" keys. Defaults to None (falls back to property_keywords). Caption matches are retained only as diagnostic metadata.
            save_failed_pdf_report (bool, optional): For `pdfs` source only. If True, save skipped/failed filename-based DOI fallback cases to a text report. Defaults to True.
            failed_pdf_report_path (str, optional): For `pdfs` source only. Custom path for failed PDF filename report. Defaults to None (uses `{folder_path}/failed_pdf_filenames.txt`).
            save_failed_automated_report (bool, optional): For automated publisher sources (elsevier, springer, iop, wiley). If True, save failed/unparseable articles to a report. Defaults to True.
            failed_automated_report_path (str, optional): Custom path for the automated failure report. Defaults to None (uses `results/article_processor_failed_articles.txt`)..
            allow_missing_doi (bool, optional): For local PDFs, assign a stable
                internal document id when no DOI can be resolved. Defaults to False.
            allow_metadata_network (bool, optional): For local PDFs, permit
                CrossRef/OpenAlex DOI and metadata lookups. Disable for a fully
                offline preprocessing run. Defaults to True.

        Raises:
            ValueErrorHandler: If property_keywords is not provided.
        """
        if property_keywords is None:
            raise ValueErrorHandler(
                message="Please provide property_keywords dictionary to proceed."
            )
        if source_list is None:
            source_list = ["elsevier", "wiley", "iop", "springer"]
        source_list = [source.lower() for source in source_list]
        routed_doi_list = {
            "elsevier": doi_list,
            "springer": doi_list,
            "wiley": doi_list,
            "iop": doi_list,
        }
        publisher_sources = {"elsevier", "springer", "wiley", "iop"}
        selected_publisher_sources = set(source_list).intersection(publisher_sources)
        if doi_list is not None and len(selected_publisher_sources) > 0:
            for src in publisher_sources:
                routed_doi_list[src] = []
            try:
                import pandas as pd

                metadata_file = f"results/{self.main_property_keyword}_metadata.csv"
                if not os.path.exists(metadata_file):
                    logger.warning(
                        f"Metadata file '{metadata_file}' not found. Using provided DOI list for all selected sources."
                    )
                    for src in publisher_sources:
                        routed_doi_list[src] = doi_list
                else:
                    metadata_df = pd.read_csv(
                        metadata_file, dtype=str, low_memory=False
                    ).fillna("")
                    if (
                        "doi" not in metadata_df.columns
                        or "general_publisher" not in metadata_df.columns
                    ):
                        logger.warning(
                            "Metadata file is missing required columns ('doi', 'general_publisher'). Using provided DOI list for all selected sources."
                        )
                        for src in publisher_sources:
                            routed_doi_list[src] = doi_list
                    else:
                        doi_to_publisher = {
                            str(row["doi"])
                            .strip(): str(row["general_publisher"])
                            .strip()
                            .lower()
                            for _, row in metadata_df.iterrows()
                            if str(row["doi"]).strip()
                        }
                        unresolved_dois = []
                        filtered_out_dois = []
                        for doi in doi_list:
                            doi_key = str(doi).strip()
                            publisher = doi_to_publisher.get(doi_key)
                            if publisher in selected_publisher_sources:
                                routed_doi_list[publisher].append(doi)
                            elif publisher is None or publisher == "":
                                unresolved_dois.append(doi)
                            else:
                                filtered_out_dois.append((doi, publisher))
                        if unresolved_dois:
                            for src in selected_publisher_sources:
                                routed_doi_list[src].extend(unresolved_dois)
                            logger.warning(
                                f"Trying {len(unresolved_dois)} DOI(s) without publisher metadata through the selected sources."
                            )
                        if filtered_out_dois:
                            logger.info(
                                f"{len(filtered_out_dois)} DOI(s) were skipped because their publisher is not in source_list."
                            )
            except Exception as e:
                logger.warning(
                    f"Failed to route DOI list by publisher from metadata: {e}. Using provided DOI list for all selected sources."
                )
                for src in publisher_sources:
                    routed_doi_list[src] = doi_list
        if "elsevier" in source_list and (
            doi_list is None or len(routed_doi_list["elsevier"]) > 0
        ):
            from comproscanner.documents.publishers.elsevier_processor import (
                ElsevierArticleProcessor,
            )

            elsevier_processor = ElsevierArticleProcessor(
                main_property_keyword=self.main_property_keyword,
                property_keywords=property_keywords,
                csv_batch_size=csv_batch_size,
                start_row=start_row,
                end_row=end_row,
                doi_list=routed_doi_list["elsevier"],
                is_save_xml=is_save_xml,
                main_figure_keywords=main_figure_keywords,
                save_failed_automated_report=save_failed_automated_report,
                failed_automated_report_path=failed_automated_report_path,
            )
            elsevier_processor.process_elsevier_articles()
        if "springer" in source_list and (
            doi_list is None or len(routed_doi_list["springer"]) > 0
        ):
            from comproscanner.documents.publishers.springer_processor import (
                SpringerArticleProcessor,
            )

            springer_processor = SpringerArticleProcessor(
                main_property_keyword=self.main_property_keyword,
                property_keywords=property_keywords,
                csv_batch_size=csv_batch_size,
                start_row=start_row,
                end_row=end_row,
                doi_list=routed_doi_list["springer"],
                is_save_xml=is_save_xml,
                main_figure_keywords=main_figure_keywords,
                save_failed_automated_report=save_failed_automated_report,
                failed_automated_report_path=failed_automated_report_path,
            )
            springer_processor.process_springer_articles()
        if "wiley" in source_list and (
            doi_list is None or len(routed_doi_list["wiley"]) > 0
        ):
            from comproscanner.documents.publishers.wiley_processor import (
                WileyArticleProcessor,
            )

            wiley_processor = WileyArticleProcessor(
                main_property_keyword=self.main_property_keyword,
                property_keywords=property_keywords,
                csv_batch_size=csv_batch_size,
                start_row=start_row,
                end_row=end_row,
                doi_list=routed_doi_list["wiley"],
                is_save_pdf=is_save_pdf,
                save_failed_automated_report=save_failed_automated_report,
                failed_automated_report_path=failed_automated_report_path,
            )
            wiley_processor.process_wiley_articles()
        if "iop" in source_list and (
            doi_list is None or len(routed_doi_list["iop"]) > 0
        ):
            from comproscanner.documents.publishers.iop_processor import (
                IOPArticleProcessor,
            )

            iop_processor = IOPArticleProcessor(
                allow_network=allow_metadata_network,
                main_property_keyword=self.main_property_keyword,
                property_keywords=property_keywords,
                csv_batch_size=csv_batch_size,
                start_row=start_row,
                end_row=end_row,
                doi_list=routed_doi_list["iop"],
                main_figure_keywords=main_figure_keywords,
                save_failed_automated_report=save_failed_automated_report,
                failed_automated_report_path=failed_automated_report_path,
            )
            iop_processor.process_iop_articles()
        if "pdfs" in source_list:
            from comproscanner.documents.publishers.pdfs_processor import PDFsProcessor

            pdf_processor = PDFsProcessor(
                folder_path=folder_path,
                main_property_keyword=self.main_property_keyword,
                property_keywords=property_keywords,
                csv_batch_size=csv_batch_size,
                save_failed_pdf_report=save_failed_pdf_report,
                failed_pdf_report_path=failed_pdf_report_path,
                allow_missing_doi=allow_missing_doi,
                allow_metadata_network=allow_metadata_network,
            )
            pdf_processor.process_pdfs()
