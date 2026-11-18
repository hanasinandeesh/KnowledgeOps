from abc import ABC, abstractmethod
from pathlib import Path

from app.modules.ingestion.schemas import ExtractedDocument


class BaseExtractor(ABC):
    """Abstract base class for document format extractors."""

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractedDocument:
        """Extract text and metadata from the given physical file.

        Raises:
            DocumentExtractionError: If file is corrupted, encrypted, or unreadable.
        """
        pass
