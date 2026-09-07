from comproscanner.utils.pdf_to_markdown_text import match_property_signal


def test_legacy_arbitrary_keyword_groups_remain_supported():
    result = match_property_signal(
        "This article reports piezoelectric properties.",
        {"piezoelectric": ["piezoelectric", "piezo"]},
    )
    assert result == ("piezoelectric", "piezoelectric")
