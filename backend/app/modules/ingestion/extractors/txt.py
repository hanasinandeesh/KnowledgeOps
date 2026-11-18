import re
from pathlib import Path

from app.modules.ingestion.cleaner import TextCleaner
from app.modules.ingestion.extractors.base import BaseExtractor
from app.modules.ingestion.schemas import (
    DocumentExtractionError,
    ExtractedDocument,
    ExtractedPage,
)


class TxtExtractor(BaseExtractor):
    """Extracts and structures plain-text and Markdown-formatted text documents."""

    def extract(self, file_path: Path) -> ExtractedDocument:
        if not file_path.exists() or not file_path.is_file():
            raise DocumentExtractionError(
                f"File not found on storage: {file_path}",
                code="STORAGE_FILE_MISSING",
            )

        try:
            raw_bytes = file_path.read_bytes()
        except Exception as e:
            raise DocumentExtractionError(
                f"Failed to read file from disk: {e}",
                code="STORAGE_FILE_READ_ERROR",
            ) from e

        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise DocumentExtractionError(
                f"File is not valid UTF-8 text: {e}",
                code="CORRUPTED_DOCUMENT",
            ) from e

        cleaned_full_text = TextCleaner.normalize(raw_text)
        if not cleaned_full_text:
            raise DocumentExtractionError(
                "Text document is empty",
                code="EMPTY_EXTRACTED_CONTENT",
            )

        # Check if the document has Markdown-style level-1 headings (# Title)
        sections = re.split(r"\n(?=#\s+)", cleaned_full_text)
        pages: list[ExtractedPage] = []

        if len(sections) > 1:
            for idx, sec in enumerate(sections, start=1):
                sec_clean = sec.strip()
                if not sec_clean:
                    continue
                first_line = sec_clean.split("\n", 1)[0]
                section_title = (
                    first_line.lstrip("#").strip()
                    if first_line.startswith("#")
                    else None
                )
                pages.append(
                    ExtractedPage(
                        page_number=idx,
                        text=sec_clean,
                        section_title=section_title,
                    )
                )
        else:
            first_line = cleaned_full_text.split("\n", 1)[0]
            section_title = (
                first_line.lstrip("#").strip() if first_line.startswith("#") else None
            )
            pages.append(
                ExtractedPage(
                    page_number=1,
                    text=cleaned_full_text,
                    section_title=section_title,
                )
            )

        TextCleaner.validate_non_empty(pages)

        metadata = {
            "format": "TXT",
            "section_count": len(pages),
        }
        return ExtractedDocument(pages=pages, metadata=metadata)
