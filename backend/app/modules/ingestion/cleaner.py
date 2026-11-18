import re
import unicodedata

from app.modules.ingestion.schemas import DocumentExtractionError, ExtractedPage


class TextCleaner:
    """Text normalization and structural sanitization for extracted document content."""

    @classmethod
    def normalize(cls, text: str) -> str:
        """Normalize unicode, strip control characters, and clean whitespace.

        Preserves paragraph breaks, headings, and indentation.
        """
        if not text:
            return ""

        # Normalize unicode characters to NFKC form (canonical
        # decomposition followed by canonical composition)
        normalized = unicodedata.normalize("NFKC", text)

        # Remove null bytes and non-printable control characters,
        # preserving newlines and tabs
        cleaned_chars = []
        for ch in normalized:
            if ch in ("\n", "\r", "\t"):
                cleaned_chars.append(ch)
            elif ch.isprintable():
                cleaned_chars.append(ch)
        normalized = "".join(cleaned_chars)

        # Standardize line endings to \n
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # Strip trailing whitespace on each line
        lines = [line.rstrip() for line in normalized.split("\n")]
        normalized = "\n".join(lines)

        # Collapse more than two consecutive newlines to two
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        return normalized.strip()

    @classmethod
    def validate_non_empty(cls, pages: list[ExtractedPage]) -> None:
        """Ensure that extracted pages contain at least some readable text."""
        total_len = sum(len(page.text.strip()) for page in pages)
        if total_len == 0:
            raise DocumentExtractionError(
                "Document contains no readable text content",
                code="EMPTY_EXTRACTED_CONTENT",
            )
