import pytest

from app.modules.ingestion.cleaner import TextCleaner
from app.modules.ingestion.schemas import DocumentExtractionError, ExtractedPage


def test_text_cleaner_unicode_normalization() -> None:
    """NFKC normalization decomposes and recomposes unicode characters consistently."""
    # Ligature fi -> f + i, fullwidth letters -> standard ASCII
    raw_text = "\ufb01nance \uff21\uff43\uff4d\uff45"
    cleaned = TextCleaner.normalize(raw_text)
    assert cleaned == "finance Acme"


def test_text_cleaner_strips_null_bytes_and_control_chars() -> None:
    """Null bytes and control chars are removed while preserving newlines/tabs."""
    raw_text = "Line 1\x00\x07\x08\nLine 2\twith\x1f tab"
    cleaned = TextCleaner.normalize(raw_text)
    assert cleaned == "Line 1\nLine 2\twith tab"


def test_text_cleaner_collapses_excessive_newlines() -> None:
    """More than two consecutive newlines are collapsed to two."""
    raw_text = "Paragraph 1\n\n\n\n\nParagraph 2\n\n\nParagraph 3"
    cleaned = TextCleaner.normalize(raw_text)
    assert cleaned == "Paragraph 1\n\nParagraph 2\n\nParagraph 3"


def test_text_cleaner_trims_trailing_whitespace_per_line() -> None:
    """Trailing spaces and tabs on individual lines are stripped."""
    raw_text = "Header    \nBody paragraph   \n   Indented line  "
    cleaned = TextCleaner.normalize(raw_text)
    assert cleaned == "Header\nBody paragraph\n   Indented line"


def test_text_cleaner_validate_non_empty_success() -> None:
    """Validation succeeds when pages contain readable characters."""
    pages = [
        ExtractedPage(page_number=1, text="First page content"),
        ExtractedPage(page_number=2, text="Second page content"),
    ]
    # Should not raise
    TextCleaner.validate_non_empty(pages)


def test_text_cleaner_validate_non_empty_raises_on_whitespace() -> None:
    """Raises EMPTY_EXTRACTED_CONTENT if all pages contain only whitespace."""
    pages = [
        ExtractedPage(page_number=1, text="   \n\t  "),
        ExtractedPage(page_number=2, text=""),
    ]
    with pytest.raises(DocumentExtractionError) as exc_info:
        TextCleaner.validate_non_empty(pages)

    assert exc_info.value.code == "EMPTY_EXTRACTED_CONTENT"
