from dataclasses import dataclass
from typing import Any


class IndexingError(Exception):
    """Exception raised during document chunking, embedding, or vector indexing."""

    def __init__(self, message: str, code: str = "INDEXING_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class TextChunk:
    """A structure-aware document text chunk ready for persistence and embedding."""

    chunk_index: int
    content: str
    content_hash: str
    page_number: int | None
    section_title: str | None
    token_count: int


@dataclass(frozen=True)
class ChunkMetadata:
    """Metadata schema stored alongside vectors in ChromaDB."""

    chunk_id: str
    organization_id: str
    document_id: str
    document_version_id: str
    department_id: str
    visibility: str
    chunk_index: int
    page_number: int
    section_title: str
    token_count: int
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary matching ChromaDB scalar metadata requirements."""
        return {
            "chunk_id": self.chunk_id,
            "organization_id": self.organization_id,
            "document_id": self.document_id,
            "document_version_id": self.document_version_id,
            "department_id": self.department_id,
            "visibility": self.visibility,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "token_count": self.token_count,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class IndexingResult:
    """Result of an indexing operation for a document version."""

    document_version_id: str
    chunk_count: int
    indexed_vector_count: int
    model_id: str
    success: bool
    error_message: str | None = None
