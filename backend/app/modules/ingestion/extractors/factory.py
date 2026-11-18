from pathlib import Path

from app.modules.ingestion.extractors.base import BaseExtractor
from app.modules.ingestion.extractors.docx import DocxExtractor
from app.modules.ingestion.extractors.pdf import PyMuPDFExtractor
from app.modules.ingestion.extractors.txt import TxtExtractor
from app.modules.ingestion.schemas import DocumentExtractionError


class ExtractorFactory:
    """Factory creating appropriate extractors based on MIME type and file extension."""

    @classmethod
    def get_extractor(
        cls,
        mime_type: str | None = None,
        filename: str | None = None,
    ) -> BaseExtractor:
        """Resolve extractor for the given MIME type or file extension."""
        clean_mime = (mime_type or "").lower().strip()
        clean_ext = Path(filename).suffix.lower() if filename else ""

        if clean_mime == "application/pdf" or clean_ext == ".pdf":
            return PyMuPDFExtractor()

        if (
            clean_mime
            in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/docx",
                "application/msword",
            )
            or clean_ext == ".docx"
        ):
            return DocxExtractor()

        if clean_mime in ("text/plain", "text/markdown") or clean_ext in (
            ".txt",
            ".md",
        ):
            return TxtExtractor()

        raise DocumentExtractionError(
            f"Unsupported document format: mime='{mime_type}', ext='{clean_ext}'",
            code="UNSUPPORTED_FORMAT",
        )
