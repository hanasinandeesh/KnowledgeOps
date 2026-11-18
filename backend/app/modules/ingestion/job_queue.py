import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.models.document import (
    Document,
    DocumentChunk,
    DocumentPage,
    DocumentVersion,
    IngestionJob,
)
from app.modules.indexing.schemas import TextChunk
from app.modules.ingestion.schemas import ExtractedDocument

logger = logging.getLogger(__name__)


class JobQueueService:
    """Service for job claiming, leases, retries, and state transitions."""

    @classmethod
    def claim_next_job(
        cls,
        db: Session,
        worker_id: str,
        lease_duration_seconds: int = 120,
    ) -> IngestionJob | None:
        """Atomically claim the next eligible ingestion job for this worker.

        Eligible jobs are either:
        1. Status 'pending' with no retry backoff or past retry backoff.
        2. Status 'processing' whose lease has expired and attempts < max_attempts.
        """
        now = datetime.now(timezone.utc)
        lease_until = now + timedelta(seconds=lease_duration_seconds)

        # Select candidate job ID
        subquery = (
            select(IngestionJob.id)
            .where(
                or_(
                    and_(
                        IngestionJob.status == "pending",
                        or_(
                            IngestionJob.next_retry_at.is_(None),
                            IngestionJob.next_retry_at <= now,
                        ),
                    ),
                    and_(
                        IngestionJob.status == "processing",
                        IngestionJob.locked_until < now,
                        IngestionJob.attempts < IngestionJob.max_attempts,
                    ),
                )
            )
            .order_by(IngestionJob.created_at.asc())
            .limit(1)
            .scalar_subquery()
        )

        update_stmt = (
            update(IngestionJob)
            .where(IngestionJob.id == subquery)
            .values(
                status="processing",
                locked_by=worker_id,
                locked_until=lease_until,
                attempts=IngestionJob.attempts + 1,
                updated_at=now,
            )
        )

        result = db.execute(update_stmt)
        db.commit()

        if result.rowcount == 0:
            return None

        # Fetch the claimed job record
        claimed_stmt = select(IngestionJob).where(
            IngestionJob.locked_by == worker_id,
            IngestionJob.status == "processing",
            IngestionJob.locked_until == lease_until,
        )
        return db.scalars(claimed_stmt).first()

    @classmethod
    def persist_pages(
        cls,
        db: Session,
        job_id: str,
        extracted_doc: ExtractedDocument,
    ) -> list[DocumentPage]:
        """Persist extracted document pages in SQLite under a short transaction."""
        job = db.get(IngestionJob, job_id)
        if not job:
            logger.error(f"Cannot persist pages for missing ingestion job: {job_id}")
            return []

        version = db.get(DocumentVersion, job.document_version_id)
        if not version:
            logger.error(
                f"Missing document version {job.document_version_id} for job {job_id}"
            )
            return []

        now = datetime.now(timezone.utc)
        # Delete existing pages for this version if re-running
        db.query(DocumentPage).filter(
            DocumentPage.document_version_id == version.id
        ).delete()

        created_pages: list[DocumentPage] = []
        for page in extracted_doc.pages:
            db_page = DocumentPage(
                id=str(uuid.uuid4()),
                organization_id=job.organization_id,
                document_id=version.document_id,
                document_version_id=version.id,
                page_number=page.page_number,
                section_title=page.section_title,
                text_content=page.text,
                char_count=page.char_count,
                created_at=now,
            )
            db.add(db_page)
            created_pages.append(db_page)

        db.commit()
        return created_pages

    @classmethod
    def complete_job_with_chunks(
        cls,
        db: Session,
        job_id: str,
        chunks: list[TextChunk],
    ) -> list[str]:
        """Persist chunks, activate version, mark document active, and complete job.

        Returns IDs of superseded document versions whose vectors can be purged.
        """
        job = db.get(IngestionJob, job_id)
        if not job:
            logger.error(f"Cannot complete missing ingestion job: {job_id}")
            return []

        version = db.get(DocumentVersion, job.document_version_id)
        if not version:
            logger.error(
                f"Missing document version {job.document_version_id} for job {job_id}"
            )
            return []

        document = db.get(Document, version.document_id)
        now = datetime.now(timezone.utc)

        # Remove existing chunks for this version if re-running
        db.query(DocumentChunk).filter(
            DocumentChunk.document_version_id == version.id
        ).delete()

        # Insert chunks into SQLite authoritative table
        for c in chunks:
            db_chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                organization_id=job.organization_id,
                document_id=version.document_id,
                document_version_id=version.id,
                department_id=document.department_id if document else None,
                chunk_index=c.chunk_index,
                content=c.content,
                content_hash=c.content_hash,
                page_number=c.page_number,
                section_title=c.section_title,
                token_count=c.token_count,
                created_at=now,
            )
            db.add(db_chunk)

        # Identify and deactivate older versions of the same document
        superseded_version_ids = list(
            db.scalars(
                select(DocumentVersion.id).where(
                    DocumentVersion.document_id == version.document_id,
                    DocumentVersion.id != version.id,
                )
            ).all()
        )
        if superseded_version_ids:
            db.execute(
                update(DocumentVersion)
                .where(DocumentVersion.id.in_(superseded_version_ids))
                .values(is_current=False)
            )

        # Activate current version
        version.is_current = True
        version.processing_status = "completed"

        # If document is still pending (initial version upload), activate document
        if document and document.status == "pending":
            document.status = "active"
            document.updated_at = now

        # Complete job
        job.status = "completed"
        job.locked_by = None
        job.locked_until = None
        job.last_error_code = None
        job.last_error_message = None
        job.updated_at = now

        db.commit()
        logger.info(
            f"Completed job {job_id} for version {version.id} "
            f"({len(chunks)} chunks persisted and activated)"
        )
        return superseded_version_ids

    @classmethod
    def complete_job(
        cls,
        db: Session,
        job_id: str,
        extracted_doc: ExtractedDocument,
    ) -> None:
        """Persist extracted pages and complete ingestion job."""
        job = db.get(IngestionJob, job_id)
        if not job:
            logger.error(f"Cannot complete missing ingestion job: {job_id}")
            return

        version = db.get(DocumentVersion, job.document_version_id)
        if not version:
            logger.error(
                f"Missing document version {job.document_version_id} for job {job_id}"
            )
            return

        document = db.get(Document, version.document_id)
        now = datetime.now(timezone.utc)

        # First, remove any existing pages for this version if re-running
        db.query(DocumentPage).filter(
            DocumentPage.document_version_id == version.id
        ).delete()

        # Insert extracted pages
        for page in extracted_doc.pages:
            db_page = DocumentPage(
                id=str(uuid.uuid4()),
                organization_id=job.organization_id,
                document_id=version.document_id,
                document_version_id=version.id,
                page_number=page.page_number,
                section_title=page.section_title,
                text_content=page.text,
                char_count=page.char_count,
                created_at=now,
            )
            db.add(db_page)

        # Update version status
        version.processing_status = "completed"

        # If document is still pending (initial version upload), activate document
        if document and document.status == "pending":
            document.status = "active"
            document.updated_at = now

        # Complete job
        job.status = "completed"
        job.locked_by = None
        job.locked_until = None
        job.last_error_code = None
        job.last_error_message = None
        job.updated_at = now

        db.commit()
        logger.info(
            f"Completed job {job_id} for version {version.id} "
            f"({len(extracted_doc.pages)} pages extracted)"
        )

    @classmethod
    def fail_job(
        cls,
        db: Session,
        job_id: str,
        error_code: str,
        error_message: str,
        is_retryable: bool = False,
        base_backoff_seconds: int = 5,
    ) -> None:
        """Handle ingestion failure with bounded retries and exponential backoff."""
        job = db.get(IngestionJob, job_id)
        if not job:
            logger.error(f"Cannot fail missing ingestion job: {job_id}")
            return

        version = db.get(DocumentVersion, job.document_version_id)
        now = datetime.now(timezone.utc)

        # Check if retryable and under attempt threshold
        if is_retryable and job.attempts < job.max_attempts:
            delay = base_backoff_seconds * (2 ** max(0, job.attempts - 1))
            job.status = "pending"
            job.next_retry_at = now + timedelta(seconds=delay)
            job.locked_by = None
            job.locked_until = None
            job.last_error_code = error_code
            job.last_error_message = error_message[:1000]
            job.updated_at = now

            if version:
                version.processing_status = "processing"

            logger.warning(
                f"Job {job_id} failed (attempt {job.attempts}/{job.max_attempts}). "
                f"Retry in {delay}s: [{error_code}] {error_message}"
            )
        else:
            # Terminal failure
            job.status = "failed"
            job.locked_by = None
            job.locked_until = None
            job.last_error_code = error_code
            job.last_error_message = error_message[:1000]
            job.updated_at = now

            if version:
                version.processing_status = "failed"

            # Notice: Previous active version remains active and untouched!
            logger.error(
                f"Job {job_id} failed terminally ({job.attempts}/{job.max_attempts}): "
                f"[{error_code}] {error_message}"
            )

        db.commit()
