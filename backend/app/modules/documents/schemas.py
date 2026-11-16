from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentVersionResponse(BaseModel):
    """Metadata for a specific physical version of a document."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    version_number: int
    original_filename: str
    mime_type: str
    file_size_bytes: int
    processing_status: str
    is_current: bool
    uploaded_at: datetime


class DocumentResponse(BaseModel):
    """Full details of an uploaded or retrieved document."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    title: str
    description: str | None = None
    document_type: str
    visibility: str
    department_id: str | None = None
    status: str
    uploaded_by: str
    current_version: DocumentVersionResponse | None = None
    ingestion_job_id: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListItem(BaseModel):
    """Summary item in document listings."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None = None
    document_type: str
    visibility: str
    department_id: str | None = None
    status: str
    uploaded_by: str
    current_version: DocumentVersionResponse | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated collection of visible documents."""

    items: list[DocumentListItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    pages: int


class DocumentArchiveResponse(BaseModel):
    """Confirmation payload returned when a document is archived."""

    id: str
    status: str
    archived_at: datetime
    message: str = "Document successfully archived"

