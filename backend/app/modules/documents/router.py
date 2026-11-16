from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.modules.auth.dependencies import (
    OrganizationContext,
    get_organization_context,
)
from app.modules.documents.schemas import (
    DocumentArchiveResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.modules.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["Document Management"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentResponse,
    summary="Upload a new document",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT file"),
    title: str = Form(..., min_length=1, max_length=255, description="Title"),
    visibility: str = Form(..., description="organization, department, or restricted"),
    description: str | None = Form(None, max_length=1000),
    department_id: str | None = Form(None, description="Department UUID"),
    document_type: str = Form("general", max_length=50, description="e.g. policy"),
    context: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Upload a PDF, DOCX, or TXT document with metadata, creating an ingestion job."""
    file_bytes = await file.read()
    return DocumentService.upload_document(
        db=db,
        context=context,
        file_bytes=file_bytes,
        original_filename=file.filename or "unknown",
        title=title,
        visibility=visibility,
        description=description,
        department_id=department_id,
        document_type=document_type,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
)
def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    visibility: str | None = Query(None, description="Filter by visibility"),
    department_id: str | None = Query(None, description="Filter by department"),
    status: str | None = Query(None, description="Status filter (active, archived)"),
    context: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """Retrieve a paginated list of documents accessible to the current user."""
    return DocumentService.list_documents(
        db=db,
        context=context,
        page=page,
        page_size=page_size,
        visibility=visibility,
        department_id=department_id,
        status=status,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
def get_document(
    document_id: str,
    context: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Fetch details and current processing status for an authorized document."""
    return DocumentService.get_document_details(
        db=db,
        context=context,
        document_id=document_id,
    )


@router.post(
    "/{document_id}/archive",
    response_model=DocumentArchiveResponse,
    summary="Archive a document",
)
def archive_document(
    document_id: str,
    context: OrganizationContext = Depends(get_organization_context),
    db: Session = Depends(get_db),
) -> DocumentArchiveResponse:
    """Archive an authorized document, removing it from active knowledge discovery."""
    doc = DocumentService.archive_document(
        db=db,
        context=context,
        document_id=document_id,
    )
    return DocumentArchiveResponse(
        id=doc.id,
        status=doc.status,
        archived_at=doc.updated_at,
        message="Document successfully archived",
    )
