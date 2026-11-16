import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    ForbiddenException,
    InvalidRequestException,
    NotFoundException,
)
from app.models.document import (
    Document,
    DocumentAccessGrant,
    DocumentVersion,
    IngestionJob,
)
from app.models.organization import Department
from app.models.user import UserDepartment
from app.modules.auth.dependencies import OrganizationContext
from app.modules.documents.schemas import (
    DocumentListItem,
    DocumentListResponse,
    DocumentResponse,
    DocumentVersionResponse,
)
from app.modules.documents.storage import DocumentStorageService
from app.modules.documents.validator import (
    sanitize_filename,
    validate_file_content,
    validate_file_extension,
)

ALLOWED_VISIBILITIES = {"organization", "department", "restricted"}


class DocumentService:
    """Business logic for document management, uploads, permissions, and lifecycle."""

    @staticmethod
    def _validate_upload_permissions(
        db: Session,
        context: OrganizationContext,
        visibility: str,
        department_id: str | None,
    ) -> None:
        """Enforce upload authorization rules based on document visibility."""
        if visibility not in ALLOWED_VISIBILITIES:
            allowed = ", ".join(sorted(ALLOWED_VISIBILITIES))
            raise InvalidRequestException(
                f"Invalid visibility '{visibility}'. Allowed values: {allowed}"
            )

        # Organization-wide uploads are restricted to admins and department managers
        if visibility == "organization":
            if context.role not in {"organization_admin", "department_manager"}:
                raise ForbiddenException(
                    "Only organization admins and department managers can upload "
                    "organization-wide documents"
                )

        # Department-specific uploads require valid department and membership
        elif visibility == "department":
            if not department_id:
                raise InvalidRequestException(
                    "department_id is required for department-specific documents"
                )

            # Confirm department belongs to caller's organization
            dept_stmt = select(Department).where(
                Department.id == department_id,
                Department.organization_id == context.organization_id,
            )
            dept = db.scalars(dept_stmt).first()
            if dept is None:
                raise NotFoundException(
                    "Department not found in current organization"
                )

            # Admins can upload to any department; otherwise caller must be a member
            if context.role != "organization_admin":
                membership_stmt = select(UserDepartment).where(
                    UserDepartment.organization_id == context.organization_id,
                    UserDepartment.user_id == context.user.id,
                    UserDepartment.department_id == department_id,
                    UserDepartment.status == "active",
                )
                user_dept = db.scalars(membership_stmt).first()
                if user_dept is None:
                    raise ForbiddenException(
                        "User is not an active member of the specified department"
                    )

        # Restricted documents can be created by admins or department managers
        elif visibility == "restricted":
            if context.role not in {"organization_admin", "department_manager"}:
                raise ForbiddenException(
                    "Only organization admins and department managers can upload "
                    "restricted documents"
                )

    @classmethod
    def upload_document(
        cls,
        db: Session,
        context: OrganizationContext,
        file_bytes: bytes,
        original_filename: str,
        title: str,
        visibility: str,
        description: str | None = None,
        department_id: str | None = None,
        document_type: str = "general",
    ) -> DocumentResponse:
        """Validate, store, and record upload with transactional safety."""
        clean_title = title.strip()
        if not clean_title:
            raise InvalidRequestException("Document title cannot be empty")

        clean_visibility = visibility.strip().lower()
        cls._validate_upload_permissions(
            db=db,
            context=context,
            visibility=clean_visibility,
            department_id=department_id,
        )

        # Validate file extension and magic-byte signatures
        safe_name = sanitize_filename(original_filename)
        extension = validate_file_extension(safe_name)
        mime_type = validate_file_content(file_bytes, extension)

        # Generate entity identifiers
        doc_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Save physical file to disk using safe UUID storage path
        storage_path, content_hash, file_size = DocumentStorageService.save_file(
            organization_id=context.organization_id,
            version_id=version_id,
            content=file_bytes,
        )

        doc_type = document_type.strip().lower() if document_type else "general"
        dept_id = department_id if clean_visibility == "department" else None

        try:
            document = Document(
                id=doc_id,
                organization_id=context.organization_id,
                title=clean_title,
                description=description.strip() if description else None,
                document_type=doc_type,
                visibility=clean_visibility,
                department_id=dept_id,
                uploaded_by=context.user.id,
                status="pending",
                created_at=now,
                updated_at=now,
            )
            db.add(document)

            version = DocumentVersion(
                id=version_id,
                organization_id=context.organization_id,
                document_id=doc_id,
                version_number=1,
                storage_path=storage_path,
                original_filename=safe_name,
                mime_type=mime_type,
                file_size_bytes=file_size,
                content_hash=content_hash,
                processing_status="pending",
                is_current=True,
                uploaded_at=now,
            )
            db.add(version)

            job = IngestionJob(
                id=job_id,
                organization_id=context.organization_id,
                document_version_id=version_id,
                status="pending",
                attempts=0,
                max_attempts=3,
                created_at=now,
                updated_at=now,
            )
            db.add(job)

            # If document is restricted, automatically grant read access to the uploader
            if clean_visibility == "restricted":
                grant = DocumentAccessGrant(
                    id=str(uuid.uuid4()),
                    organization_id=context.organization_id,
                    document_id=doc_id,
                    subject_type="user",
                    subject_id=context.user.id,
                    permission="read",
                    granted_by=context.user.id,
                    created_at=now,
                )
                db.add(grant)

            db.flush()
        except Exception:
            # Clean up the file from disk so no orphaned file remains on DB failure
            DocumentStorageService.delete_file(storage_path)
            raise

        version_dto = DocumentVersionResponse(
            id=version.id,
            version_number=version.version_number,
            original_filename=version.original_filename,
            mime_type=version.mime_type,
            file_size_bytes=version.file_size_bytes,
            processing_status=version.processing_status,
            is_current=version.is_current,
            uploaded_at=version.uploaded_at,
        )

        return DocumentResponse(
            id=document.id,
            organization_id=document.organization_id,
            title=document.title,
            description=document.description,
            document_type=document.document_type,
            visibility=document.visibility,
            department_id=document.department_id,
            status=document.status,
            uploaded_by=document.uploaded_by,
            current_version=version_dto,
            ingestion_job_id=job.id,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    @classmethod
    def get_document_details(
        cls,
        db: Session,
        context: OrganizationContext,
        document_id: str,
    ) -> DocumentResponse:
        """Fetch document details enforcing tenant isolation and visibility rules."""
        stmt = (
            select(Document)
            .options(joinedload(Document.versions))
            .where(
                Document.id == document_id,
                Document.organization_id == context.organization_id,
                Document.status != "deleted",
            )
        )
        document = db.scalars(stmt).first()

        # If document does not exist in this tenant, return 404
        if document is None:
            raise NotFoundException("Document not found")

        # Enforce visibility rules
        if document.visibility == "organization":
            # Accessible to all active members of the tenant
            pass

        elif document.visibility == "department":
            # Accessible if caller is admin, in department, or has explicit grant
            has_access = False
            if context.role == "organization_admin":
                has_access = True
            elif document.department_id:
                user_dept_stmt = select(UserDepartment).where(
                    UserDepartment.organization_id == context.organization_id,
                    UserDepartment.user_id == context.user.id,
                    UserDepartment.department_id == document.department_id,
                    UserDepartment.status == "active",
                )
                if db.scalars(user_dept_stmt).first() is not None:
                    has_access = True

            if not has_access:
                # Check explicit grant
                grant_stmt = select(DocumentAccessGrant).where(
                    DocumentAccessGrant.document_id == document.id,
                    DocumentAccessGrant.organization_id == context.organization_id,
                    DocumentAccessGrant.revoked_at.is_(None),
                    or_(
                        and_(
                            DocumentAccessGrant.subject_type == "user",
                            DocumentAccessGrant.subject_id == context.user.id,
                        ),
                        and_(
                            DocumentAccessGrant.subject_type == "role",
                            DocumentAccessGrant.subject_id == context.role,
                        ),
                    ),
                )
                if db.scalars(grant_stmt).first() is not None:
                    has_access = True

            if not has_access:
                raise ForbiddenException(
                    "Access to this department document is forbidden"
                )

        elif document.visibility == "restricted":
            # Restricted documents require explicit user or role grant
            # Org admin DOES NOT automatically have access without a grant
            grant_stmt = select(DocumentAccessGrant).where(
                DocumentAccessGrant.document_id == document.id,
                DocumentAccessGrant.organization_id == context.organization_id,
                DocumentAccessGrant.revoked_at.is_(None),
                or_(
                    and_(
                        DocumentAccessGrant.subject_type == "user",
                        DocumentAccessGrant.subject_id == context.user.id,
                    ),
                    and_(
                        DocumentAccessGrant.subject_type == "role",
                        DocumentAccessGrant.subject_id == context.role,
                    ),
                ),
            )
            if db.scalars(grant_stmt).first() is None:
                raise ForbiddenException(
                    "Access to this restricted document is forbidden"
                )

        # Find current version
        current_version = next(
            (v for v in document.versions if v.is_current),
            document.versions[0] if document.versions else None,
        )
        version_dto = None
        if current_version:
            version_dto = DocumentVersionResponse(
                id=current_version.id,
                version_number=current_version.version_number,
                original_filename=current_version.original_filename,
                mime_type=current_version.mime_type,
                file_size_bytes=current_version.file_size_bytes,
                processing_status=current_version.processing_status,
                is_current=current_version.is_current,
                uploaded_at=current_version.uploaded_at,
            )

        return DocumentResponse(
            id=document.id,
            organization_id=document.organization_id,
            title=document.title,
            description=document.description,
            document_type=document.document_type,
            visibility=document.visibility,
            department_id=document.department_id,
            status=document.status,
            uploaded_by=document.uploaded_by,
            current_version=version_dto,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    @classmethod
    def list_documents(
        cls,
        db: Session,
        context: OrganizationContext,
        page: int = 1,
        page_size: int = 20,
        visibility: str | None = None,
        department_id: str | None = None,
        status: str | None = None,
    ) -> DocumentListResponse:
        """List documents visible to the current user within their tenant."""
        safe_page = max(1, page)
        safe_page_size = min(max(1, page_size), 100)

        # Subquery for user's active departments
        user_dept_subquery = (
            select(UserDepartment.department_id)
            .where(
                UserDepartment.organization_id == context.organization_id,
                UserDepartment.user_id == context.user.id,
                UserDepartment.status == "active",
            )
            .scalar_subquery()
        )

        # Subquery for explicit document grants to user or role
        granted_doc_subquery = (
            select(DocumentAccessGrant.document_id)
            .where(
                DocumentAccessGrant.organization_id == context.organization_id,
                DocumentAccessGrant.revoked_at.is_(None),
                or_(
                    and_(
                        DocumentAccessGrant.subject_type == "user",
                        DocumentAccessGrant.subject_id == context.user.id,
                    ),
                    and_(
                        DocumentAccessGrant.subject_type == "role",
                        DocumentAccessGrant.subject_id == context.role,
                    ),
                ),
            )
            .scalar_subquery()
        )

        # Permission visibility conditions
        dept_condition = and_(
            Document.visibility == "department",
            or_(
                Document.department_id.in_(user_dept_subquery),
                Document.id.in_(granted_doc_subquery),
                context.role == "organization_admin",
            ),
        )

        restricted_condition = and_(
            Document.visibility == "restricted",
            Document.id.in_(granted_doc_subquery),
        )

        visibility_filter = or_(
            Document.visibility == "organization",
            dept_condition,
            restricted_condition,
        )

        # Build base filter
        filters = [
            Document.organization_id == context.organization_id,
            visibility_filter,
        ]

        if status:
            filters.append(Document.status == status)
        else:
            # By default exclude deleted documents
            filters.append(Document.status != "deleted")

        if visibility:
            filters.append(Document.visibility == visibility)

        if department_id:
            filters.append(Document.department_id == department_id)

        # Count total matches
        count_stmt = select(func.count(Document.id)).where(*filters)
        total = db.scalar(count_stmt) or 0

        # Query paginated documents
        query = (
            select(Document)
            .options(joinedload(Document.versions))
            .where(*filters)
            .order_by(desc(Document.created_at))
            .offset((safe_page - 1) * safe_page_size)
            .limit(safe_page_size)
        )
        documents = db.scalars(query).unique().all()

        items: list[DocumentListItem] = []
        for doc in documents:
            current_v = next(
                (v for v in doc.versions if v.is_current),
                doc.versions[0] if doc.versions else None,
            )
            version_dto = None
            if current_v:
                version_dto = DocumentVersionResponse(
                    id=current_v.id,
                    version_number=current_v.version_number,
                    original_filename=current_v.original_filename,
                    mime_type=current_v.mime_type,
                    file_size_bytes=current_v.file_size_bytes,
                    processing_status=current_v.processing_status,
                    is_current=current_v.is_current,
                    uploaded_at=current_v.uploaded_at,
                )

            items.append(
                DocumentListItem(
                    id=doc.id,
                    title=doc.title,
                    description=doc.description,
                    document_type=doc.document_type,
                    visibility=doc.visibility,
                    department_id=doc.department_id,
                    status=doc.status,
                    uploaded_by=doc.uploaded_by,
                    current_version=version_dto,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                )
            )

        total_pages = math.ceil(total / safe_page_size) if total > 0 else 1

        return DocumentListResponse(
            items=items,
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            pages=total_pages,
        )

    @classmethod
    def archive_document(
        cls,
        db: Session,
        context: OrganizationContext,
        document_id: str,
    ) -> Document:
        """Archive a document if caller is admin, uploader, or manager."""
        stmt = select(Document).where(
            Document.id == document_id,
            Document.organization_id == context.organization_id,
            Document.status != "deleted",
        )
        document = db.scalars(stmt).first()

        if document is None:
            raise NotFoundException("Document not found")

        # Authorization: caller must be org admin, uploader, or department manager
        is_authorized = False
        if context.role == "organization_admin":
            is_authorized = True
        elif document.uploaded_by == context.user.id:
            is_authorized = True
        elif context.role == "department_manager" and document.department_id:
            # Check manager's department
            mgr_dept = select(UserDepartment).where(
                UserDepartment.organization_id == context.organization_id,
                UserDepartment.user_id == context.user.id,
                UserDepartment.department_id == document.department_id,
                UserDepartment.status == "active",
            )
            if db.scalars(mgr_dept).first() is not None:
                is_authorized = True

        if not is_authorized:
            raise ForbiddenException(
                "You do not have permission to archive this document"
            )

        document.status = "archived"
        document.updated_at = datetime.now(timezone.utc)
        db.flush()
        return document
