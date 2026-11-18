from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.modules.ingestion.cleaner import TextCleaner
from app.modules.ingestion.extractors.base import BaseExtractor
from app.modules.ingestion.schemas import (
    DocumentExtractionError,
    ExtractedDocument,
    ExtractedPage,
)


class DocxExtractor(BaseExtractor):
    """Extracts text, headings, and tables from DOCX documents using python-docx."""

    def extract(self, file_path: Path) -> ExtractedDocument:
        if not file_path.exists() or not file_path.is_file():
            raise DocumentExtractionError(
                f"File not found on storage: {file_path}",
                code="STORAGE_FILE_MISSING",
            )

        try:
            doc = Document(str(file_path))
        except Exception as e:
            raise DocumentExtractionError(
                f"Corrupted or invalid DOCX package: {e}",
                code="CORRUPTED_DOCUMENT",
            ) from e

        pages: list[ExtractedPage] = []
        current_section_title: str | None = None
        current_lines: list[str] = []
        page_index = 1

        def flush_section() -> None:
            nonlocal current_lines, current_section_title, page_index
            text = "\n".join(current_lines).strip()
            if text:
                cleaned = TextCleaner.normalize(text)
                if cleaned:
                    pages.append(
                        ExtractedPage(
                            page_number=page_index,
                            text=cleaned,
                            section_title=current_section_title,
                        )
                    )
                    page_index += 1
            current_lines = []

        try:
            # Iterate through body elements in document order
            for child in doc.element.body:
                if isinstance(child, CT_P):
                    p = Paragraph(child, doc)
                    text = p.text.strip()
                    if not text:
                        continue

                    style_name = p.style.name if p.style else ""
                    # Check if this paragraph is a major heading
                    if style_name.startswith("Heading 1") or (
                        style_name.startswith("Heading") and not current_section_title
                    ):
                        # Flush previous section if we already have lines
                        if current_lines:
                            flush_section()
                        current_section_title = text
                        current_lines.append(f"# {text}")
                    elif style_name.startswith("Heading"):
                        current_lines.append(f"## {text}")
                    else:
                        current_lines.append(text)

                elif isinstance(child, CT_Tbl):
                    t = Table(child, doc)
                    table_rows: list[str] = []
                    for row in t.rows:
                        row_cells = [
                            cell.text.strip().replace("\n", " ") for cell in row.cells
                        ]
                        table_rows.append(" | ".join(row_cells))
                    if table_rows:
                        current_lines.append("\n".join(table_rows))

            # Flush the final section
            if current_lines:
                flush_section()

            TextCleaner.validate_non_empty(pages)

            metadata: dict[str, Any] = {
                "format": "DOCX",
                "section_count": len(pages),
            }
            return ExtractedDocument(pages=pages, metadata=metadata)

        except DocumentExtractionError:
            raise
        except Exception as e:
            raise DocumentExtractionError(
                f"Failed to extract content from DOCX: {e}",
                code="EXTRACTION_FAILED",
            ) from e
