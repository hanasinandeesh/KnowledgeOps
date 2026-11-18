from dataclasses import dataclass, field
from typing import Any


class DocumentExtractionError(Exception):
    """Exception raised when document extraction or normalization fails."""

    def __init__(self, message: str, code: str = "EXTRACTION_FAILED"):
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass
class ExtractedPage:
    """Represents text and metadata extracted from a document page or section."""

    page_number: int | None
    text: str
    section_title: str | None = None
    char_count: int = 0

    def __post_init__(self) -> None:
        if not self.char_count:
            self.char_count = len(self.text)


@dataclass
class ExtractedDocument:
    """Represents complete extracted document content and structural pages."""

    pages: list[ExtractedPage] = field(default_factory=list)
    total_characters: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.total_characters and self.pages:
            self.total_characters = sum(p.char_count for p in self.pages)
