"""
test_wiley_processor.py

Author: Aritra Roy
Email: contact@aritraroy.live
Website: https://aritraroy.live
Date: 31-03-2025
"""

import pytest

pytest.importorskip("docling")
import os
import time
import pandas as pd
from unittest.mock import patch, Mock, MagicMock
from comproscanner._errors import ValueErrorHandler, BaseError, KeyboardInterruptHandler
from comproscanner.documents.publishers.wiley_processor import WileyArticleProcessor


@pytest.fixture
def sample_pdf_content():
    """Fixture to load sample PDF content from a file"""
    sample_pdf_path = os.path.join(
        os.path.dirname(__file__), "../../fixtures", "wiley_test.pdf"
    )
    with open(sample_pdf_path, "rb") as f:
        pdf_content = f.read()
    return pdf_content


@pytest.fixture
def sample_df():
    """Fixture to create a sample DataFrame for testing"""
    return pd.DataFrame(
        {
            "doi": ["10.1002/article1", "10.1002/article2", "10.1002/article3"],
            "article_title": ["Article 1", "Article 2", "Article 3"],
            "publication_name": ["Journal A", "Journal B", "Journal C"],
            "general_publisher": ["wiley", "wiley", "wiley"],
            "metadata_publisher": [
                "Wiley Publishing",
                "Wiley Publishing",
                "Wiley Publishing",
            ],
            "is_property_mentioned": ["0", "0", "0"],
        }
    )


@pytest.fixture
def property_keywords():
    """Fixture to provide property keywords dictionary"""
    return {
        "exact_keywords": ["piezoelectric", "ferroelectric"],
        "substring_keywords": [" piezo ", " ferro "],
    }


@pytest.fixture
def wiley_processor(monkeypatch, property_keywords):
    """Fixture to create a WileyArticleProcessor instance with test parameters"""
    monkeypatch.setenv("WILEY_API_KEY", "dummy_wiley_api_key")
    return WileyArticleProcessor(
        main_property_keyword="piezoelectric", property_keywords=property_keywords
    )


def test_init_without_api_key(monkeypatch, property_keywords):
    """Test initialization without API key"""
    monkeypatch.delenv("WILEY_API_KEY", raising=False)
    monkeypatch.setattr(BaseError, "exit_program", lambda self: None)
    with pytest.raises(ValueErrorHandler) as exc_info:
        WileyArticleProcessor(
            main_property_keyword="test", property_keywords=property_keywords
        )
    assert "WILEY_API_KEY is not set in the environment variables" in str(
        exc_info.value
    )


def test_init_without_keyword(monkeypatch, property_keywords):
    """Test initialization without main property keyword"""
    monkeypatch.setenv("WILEY_API_KEY", "dummy_wiley_api_key")
    monkeypatch.setattr(BaseError, "exit_program", lambda self: None)
    with pytest.raises(ValueErrorHandler) as exc_info:
        WileyArticleProcessor(property_keywords=property_keywords)
    assert "main_property_keyword" in str(exc_info.value)


def test_init_without_property_keywords(monkeypatch):
    """Test initialization without property keywords"""
    monkeypatch.setenv("WILEY_API_KEY", "dummy_wiley_api_key")
    monkeypatch.setattr(BaseError, "exit_program", lambda self: None)
    with pytest.raises(ValueErrorHandler) as exc_info:
        WileyArticleProcessor(main_property_keyword="test")
    assert "property_keywords" in str(exc_info.value)


def test_headers_setup(wiley_processor):
    """Test that headers are properly set up"""
    assert wiley_processor.headers["X-ELS-APIKey"] == "dummy_wiley_api_key"
    assert wiley_processor.headers["Accept"] == "application/xml"


def test_load_and_preprocess_data(wiley_processor, sample_df, monkeypatch):
    """Test loading and preprocessing of data"""
    monkeypatch.setattr(pd, "read_csv", lambda *args, **kwargs: sample_df)
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    monkeypatch.setattr(os, "makedirs", lambda *args, **kwargs: None)
    wiley_processor._load_and_preprocess_data()
    assert len(wiley_processor.df) == 3
    assert all(wiley_processor.df["general_publisher"].str.lower() == "wiley")


def test_load_and_preprocess_data_with_row_limits(
    wiley_processor, sample_df, monkeypatch
):
    """Test loading and preprocessing with row limits"""
    monkeypatch.setattr(pd, "read_csv", lambda *args, **kwargs: sample_df)
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    monkeypatch.setattr(os, "makedirs", lambda *args, **kwargs: None)
    wiley_processor.start_row = 0
    wiley_processor.end_row = 1
    wiley_processor._load_and_preprocess_data()
    assert len(wiley_processor.df) == 1
    assert wiley_processor.df.iloc[0]["doi"] == "10.1002/article1"


def test_load_and_preprocess_with_processed_dois(
    wiley_processor, sample_df, monkeypatch
):
    """Test loading and preprocessing with already processed DOIs"""
    monkeypatch.setattr(
        pd,
        "read_csv",
        lambda *args, **kwargs: (
            sample_df
            if args[0] == wiley_processor.metadata_csv_filename
            else pd.DataFrame({"doi": ["10.1002/article1"]})
        ),
    )
    monkeypatch.setattr(os.path, "exists", lambda path: True)
    monkeypatch.setattr(os, "makedirs", lambda *args, **kwargs: None)
    wiley_processor._load_and_preprocess_data()
    assert len(wiley_processor.df) == 2
    assert "10.1002/article1" not in wiley_processor.df["doi"].values


@pytest.mark.integration
def test_send_request_success(wiley_processor, sample_pdf_content, monkeypatch, mocker):
    """Test successful API request"""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.content = sample_pdf_content
    mocker.patch("requests.get", return_value=mock_response)
    mock_temp_file = mocker.MagicMock()
    mock_temp_file.name = "/tmp/test.pdf"
    mock_temp_file.__enter__.return_value = mock_temp_file
    mocker.patch("tempfile.NamedTemporaryFile", return_value=mock_temp_file)
    result = wiley_processor._send_request("10.1002/test")
    assert result == "/tmp/test.pdf"
    wiley_processor.is_save_pdf = True
    mocker.patch("builtins.open", mocker.mock_open())
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch("os.makedirs", return_value=None)
    result = wiley_processor._send_request("10.1002/test")
    assert "downloaded_files/pdfs/wiley" in result


@pytest.mark.integration
def test_send_request_rate_limit(wiley_processor, mocker):
    """Test API rate limit handling"""
    mock_response = mocker.Mock()
    mock_response.status_code = 429
    mocker.patch("requests.get", return_value=mock_response)
    result = wiley_processor._send_request("10.1002/test")
    assert result is None
    assert wiley_processor.is_exceeded is True


@pytest.mark.integration
def test_process_articles(
    wiley_processor, sample_df, sample_pdf_content, mocker, monkeypatch, tmp_path
):
    """Test processing articles workflow"""
    mocker.patch.object(wiley_processor, "_load_and_preprocess_data", return_value=None)
    wiley_processor.df = sample_df
    pdf_file = tmp_path / "test.pdf"
    with open(pdf_file, "wb") as f:
        f.write(sample_pdf_content)
    mocker.patch.object(wiley_processor, "_send_request", return_value=str(pdf_file))
    mocker.patch(
        "comproscanner.documents.metadata.get_paper_metadata_from_openalex",
        return_value=("Test Title", "Test Journal", "Wiley"),
    )
    mocker.patch.object(
        wiley_processor.sql_db_manager, "write_to_sql_db", return_value=None
    )
    mocker.patch.object(
        wiley_processor.article_store, "write_to_csv", return_value=None
    )

    def mock_process_articles(*args, **kwargs):
        wiley_processor.valid_property_articles = 3

    mocker.patch.object(
        wiley_processor, "_process_articles", side_effect=mock_process_articles
    )
    wiley_processor.process_wiley_articles()
    assert wiley_processor.valid_property_articles == 3


@pytest.mark.integration
def test_process_articles_with_doi_list(
    wiley_processor, sample_df, sample_pdf_content, mocker, tmp_path
):
    """Test processing articles with specific DOI list"""

    def mock_process_articles(*args, **kwargs):
        wiley_processor.valid_property_articles = 1

    mocker.patch.object(
        wiley_processor, "_process_articles", side_effect=mock_process_articles
    )
    wiley_processor.doi_list = ["10.1002/testdoi"]
    wiley_processor.process_wiley_articles()
    assert wiley_processor.valid_property_articles == 1


@pytest.mark.integration
def test_process_with_timeout_handling(wiley_processor, monkeypatch, mocker):
    """Test processing with timeout handling"""
    mock_timeout_file_content = "10.1002/timeout1\n10.1002/timeout2"
    mock_file = mocker.mock_open(read_data=mock_timeout_file_content)
    mocker.patch("builtins.open", mock_file)
    file_exists_counter = [True, False]
    monkeypatch.setattr(
        os.path,
        "isfile",
        lambda path: (
            file_exists_counter.pop(0)
            if path == wiley_processor.timeout_file
            else False
        ),
    )
    monkeypatch.setattr(os.path, "exists", lambda path: True)
    mocker.patch("os.remove", return_value=None)
    mocker.patch.object(wiley_processor, "_process_articles", return_value=None)
    wiley_processor._process_with_timeout_handling()
    assert wiley_processor.doi_list == ["10.1002/timeout1", "10.1002/timeout2"]
    assert wiley_processor._process_articles.call_count == 1


@pytest.mark.integration
def test_keyboard_interrupt_handling(wiley_processor, sample_df, monkeypatch, mocker):
    """Test handling of keyboard interrupts"""
    mocker.patch.object(wiley_processor, "_load_and_preprocess_data", return_value=None)
    wiley_processor.df = sample_df
    mocker.patch.object(wiley_processor, "_send_request", side_effect=KeyboardInterrupt)
    with pytest.raises(KeyboardInterruptHandler):
        wiley_processor._process_articles()


@pytest.mark.integration
def test_complete_workflow(wiley_processor, monkeypatch, mocker):
    """Test the complete workflow"""
    mocker.patch.object(wiley_processor, "_process_articles", return_value=None)
    mocker.patch.object(
        wiley_processor, "_process_with_timeout_handling", return_value=None
    )
    wiley_processor.process_wiley_articles()
    assert wiley_processor._process_articles.call_count == 1
    assert wiley_processor._process_with_timeout_handling.call_count == 1
