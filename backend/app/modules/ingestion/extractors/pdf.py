from pathlib import Path

import pymupdf

from app.modules.ingestion.cleaner import TextCleaner
from app.modules.ingestion.extractors.base import BaseExtractor
from app.modules.ingestion.schemas import (
    DocumentExtractionError,
    ExtractedDocument,
    ExtractedPage,
)


class PyMuPDFExtractor(BaseExtractor):
    """Extracts text and page numbers from PDF files using PyMuPDF (fitz)."""

    def extract(self, file_path: Path) -> ExtractedDocument:
        if not file_path.exists() or not file_path.is_file():
            raise DocumentExtractionError(
                f"File not found on storage: {file_path}",
                code="STORAGE_FILE_MISSING",
            )

        doc = None
        try:
            doc = pymupdf.open(str(file_path))
        except Exception as e:
            raise DocumentExtractionError(
                f"Corrupted or unreadable PDF: {e}",
                code="CORRUPTED_DOCUMENT",
            ) from e

        try:
            if doc.is_encrypted or doc.needs_pass:
                raise DocumentExtractionError(
                    "PDF file is encrypted or password-protected",
                    code="ENCRYPTED_PDF",
                )

            pages: list[ExtractedPage] = []
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                raw_text = page.get_text("text") or ""
                cleaned_text = TextCleaner.normalize(raw_text)

                if cleaned_text:
                    pages.append(
                        ExtractedPage(
                            page_number=page_idx + 1,
                            text=cleaned_text,
                            section_title=None,
                        )
                    )

            TextCleaner.validate_non_empty(pages)

            metadata = {
                "format": "PDF",
                "page_count": len(doc),
                "author": doc.metadata.get("author") if doc.metadata else None,
                "title": doc.metadata.get("title") if doc.metadata else None,
            }

            return ExtractedDocument(pages=pages, metadata=metadata)
        finally:
            if doc is not None:
                doc.close()
