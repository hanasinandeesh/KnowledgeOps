import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pymupdf
from sqlalchemy.orm import Session, sessionmaker

from app.models.document import Document, DocumentPage, DocumentVersion, IngestionJob
from app.models.organization import Organization
from app.models.user import User
from app.modules.documents.storage import DocumentStorageService
from app.modules.ingestion.job_queue import JobQueueService
from app.modules.ingestion.worker import IngestionWorker


def create_test_entities(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    version_number: int = 1,
    existing_doc_id: str | None = None,
) -> tuple[Document, DocumentVersion, IngestionJob]:
    """Helper to save a physical document file and create Document, Version, and Job."""
    doc_id = existing_doc_id or str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Save to disk using DocumentStorageService
    storage_path, content_hash, file_size = DocumentStorageService.save_file(
        organization_id=test_org.id,
        version_id=version_id,
        content=file_bytes,
    )

    if not existing_doc_id:
        doc = Document(
            id=doc_id,
            organization_id=test_org.id,
            title="Test Document",
            document_type="policy",
            visibility="organization",
            uploaded_by=test_user.id,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        db_session.add(doc)
    else:
        doc = db_session.get(Document, existing_doc_id)

    version = DocumentVersion(
        id=version_id,
        organization_id=test_org.id,
        document_id=doc_id,
        version_number=version_number,
        storage_path=storage_path,
        original_filename=filename,
        mime_type=mime_type,
        file_size_bytes=file_size,
        content_hash=content_hash,
        processing_status="pending",
        is_current=True,
        uploaded_at=now,
    )
    db_session.add(version)

    job = IngestionJob(
        id=job_id,
        organization_id=test_org.id,
        document_version_id=version_id,
        status="pending",
        attempts=0,
        max_attempts=3,
        created_at=now,
        updated_at=now,
    )
    db_session.add(job)
    db_session.commit()

    return doc, version, job


# ==========================================
# Job Queue Unit Tests
# ==========================================


def test_job_queue_claim_single_job(
    db_session: Session,
    test_user: User,
    test_org: Organization,
) -> None:
    """A worker successfully claims a pending job with lease and attempt increment."""
    _, _, job = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Sample content",
        filename="test.txt",
        mime_type="text/plain",
    )

    worker_id = "test-worker-1"
    claimed = JobQueueService.claim_next_job(
        db=db_session,
        worker_id=worker_id,
        lease_duration_seconds=60,
    )

    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "processing"
    assert claimed.locked_by == worker_id
    assert claimed.attempts == 1
    assert claimed.locked_until is not None


def test_job_queue_concurrent_claiming_prevents_duplicate(
    db_session: Session,
    test_user: User,
    test_org: Organization,
) -> None:
    """When a job is already claimed, a second worker cannot claim it."""
    create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Sample content",
        filename="test.txt",
        mime_type="text/plain",
    )

    claimed_1 = JobQueueService.claim_next_job(
        db=db_session,
        worker_id="worker-alpha",
        lease_duration_seconds=60,
    )
    assert claimed_1 is not None

    claimed_2 = JobQueueService.claim_next_job(
        db=db_session,
        worker_id="worker-beta",
        lease_duration_seconds=60,
    )
    assert claimed_2 is None


def test_job_queue_recovers_expired_lease(
    db_session: Session,
    test_user: User,
    test_org: Organization,
) -> None:
    """An uncompleted job with an expired lease is automatically re-claimed."""
    _, _, job = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Sample content",
        filename="test.txt",
        mime_type="text/plain",
    )

    # Simulate crashed worker holding expired lease
    job.status = "processing"
    job.locked_by = "dead-worker"
    job.locked_until = datetime.now(timezone.utc) - timedelta(seconds=10)
    job.attempts = 1
    db_session.commit()

    reclaimed = JobQueueService.claim_next_job(
        db=db_session,
        worker_id="recovering-worker",
        lease_duration_seconds=60,
    )

    assert reclaimed is not None
    assert reclaimed.id == job.id
    assert reclaimed.locked_by == "recovering-worker"
    assert reclaimed.attempts == 2


def test_job_queue_respects_backoff_delay(
    db_session: Session,
    test_user: User,
    test_org: Organization,
) -> None:
    """A pending job with next_retry_at in the future is not claimed."""
    _, _, job = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Sample content",
        filename="test.txt",
        mime_type="text/plain",
    )

    job.status = "pending"
    job.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    db_session.commit()

    claimed = JobQueueService.claim_next_job(
        db=db_session,
        worker_id="worker-1",
        lease_duration_seconds=60,
    )
    assert claimed is None


# ==========================================
# Worker End-to-End Processing Tests
# ==========================================


def test_worker_process_txt_success(
    db_session: Session,
    test_user: User,
    test_org: Organization,
) -> None:
    """Worker extracts TXT content, saves DocumentPages, and completes job."""
    content = "# Section 1\nFirst paragraph.\n\n# Section 2\nSecond paragraph."
    doc, version, job = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=content.encode("utf-8"),
        filename="sample.txt",
        mime_type="text/plain",
    )

    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="unit-test-worker", session_factory=session_factory
    )
    did_work = worker.process_one_job()
    assert did_work is True

    # Refresh records
    db_session.refresh(job)
    db_session.refresh(version)
    db_session.refresh(doc)

    assert job.status == "completed"
    assert job.locked_by is None
    assert version.processing_status == "completed"
    assert doc.status == "active"

    # Verify extracted pages in SQLite
    pages = (
        db_session.query(DocumentPage)
        .filter(DocumentPage.document_version_id == version.id)
        .order_by(DocumentPage.page_number)
        .all()
    )
    assert len(pages) == 2
    assert pages[0].section_title == "Section 1"
    assert "First paragraph." in pages[0].text_content
    assert pages[1].section_title == "Section 2"
    assert "Second paragraph." in pages[1].text_content


def test_worker_process_pdf_success(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    tmp_path: Path,
) -> None:
    """Worker successfully extracts multi-page PDF, preserving page numbers."""
    pdf_doc = pymupdf.open()
    p1 = pdf_doc.new_page()
    p1.insert_text((50, 50), "First Page Policy Text")
    p2 = pdf_doc.new_page()
    p2.insert_text((50, 50), "Second Page Appendix Text")
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    doc, version, job = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=pdf_bytes,
        filename="policy.pdf",
        mime_type="application/pdf",
    )

    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="unit-test-worker", session_factory=session_factory
    )
    did_work = worker.process_one_job()
    assert did_work is True

    db_session.refresh(job)
    db_session.refresh(version)

    assert job.status == "completed"
    assert version.processing_status == "completed"

    pages = (
        db_session.query(DocumentPage)
        .filter(DocumentPage.document_version_id == version.id)
        .order_by(DocumentPage.page_number)
        .all()
    )
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "First Page Policy Text" in pages[0].text_content
    assert pages[1].page_number == 2
    assert "Second Page Appendix Text" in pages[1].text_content


def test_worker_corrupted_file_terminal_failure(
    db_session: Session,
    test_user: User,
    test_org: Organization,
) -> None:
    """Corrupted file results in immediate terminal failure without retry loops."""
    corrupt_bytes = b"%PDF-1.5 corrupted binary trash data"
    doc, version, job = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=corrupt_bytes,
        filename="corrupted.pdf",
        mime_type="application/pdf",
    )

    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="unit-test-worker", session_factory=session_factory
    )
    did_work = worker.process_one_job()
    assert did_work is True

    db_session.refresh(job)
    db_session.refresh(version)

    assert job.status == "failed"
    assert job.last_error_code == "CORRUPTED_DOCUMENT"
    assert version.processing_status == "failed"
    assert job.locked_by is None


def test_worker_transient_failure_retries_with_backoff(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    monkeypatch,
) -> None:
    """Transient error marks job pending with next_retry_at set."""
    doc, version, job = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Hello text",
        filename="test.txt",
        mime_type="text/plain",
    )

    from app.modules.ingestion.extractors.txt import TxtExtractor
    from app.modules.ingestion.schemas import DocumentExtractionError

    def mock_extract(self, path):
        raise DocumentExtractionError("Disk I/O error", code="STORAGE_FILE_READ_ERROR")

    monkeypatch.setattr(TxtExtractor, "extract", mock_extract)

    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="unit-test-worker",
        base_backoff_seconds=10,
        session_factory=session_factory,
    )
    did_work = worker.process_one_job()
    assert did_work is True

    db_session.refresh(job)
    db_session.refresh(version)

    assert job.status == "pending"
    assert job.attempts == 1
    assert job.next_retry_at is not None
    assert job.last_error_code == "STORAGE_FILE_READ_ERROR"


def test_worker_terminal_failure_when_max_attempts_exceeded(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    monkeypatch,
) -> None:
    """Transient error becomes terminal when attempts reaches max_attempts."""
    doc, version, job = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Hello text",
        filename="test.txt",
        mime_type="text/plain",
    )

    # Simulate already at attempt 2 of 3
    job.attempts = 2
    db_session.commit()

    from app.modules.ingestion.extractors.txt import TxtExtractor
    from app.modules.ingestion.schemas import DocumentExtractionError

    def mock_extract(self, path):
        raise DocumentExtractionError("Disk I/O error", code="STORAGE_FILE_READ_ERROR")

    monkeypatch.setattr(TxtExtractor, "extract", mock_extract)

    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="unit-test-worker", session_factory=session_factory
    )
    did_work = worker.process_one_job()
    assert did_work is True

    db_session.refresh(job)
    db_session.refresh(version)

    assert job.status == "failed"
    assert job.attempts == 3
    assert version.processing_status == "failed"


def test_worker_preserves_previous_valid_version_on_failure(
    db_session: Session,
    test_user: User,
    test_org: Organization,
) -> None:
    """When version 2 fails ingestion, version 1 remains active and current."""
    # 1. Version 1 succeeded previously
    doc, v1, job1 = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Version 1 valid policy text",
        filename="policy_v1.txt",
        mime_type="text/plain",
        version_number=1,
    )
    doc.status = "active"
    v1.processing_status = "completed"
    v1.is_current = True
    job1.status = "completed"
    db_session.commit()

    # 2. Upload version 2 which is corrupt
    _, v2, job2 = create_test_entities(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Corrupted bytes",
        filename="policy_v2.pdf",
        mime_type="application/pdf",
        version_number=2,
        existing_doc_id=doc.id,
    )

    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="unit-test-worker", session_factory=session_factory
    )
    did_work = worker.process_one_job()
    assert did_work is True

    db_session.refresh(v1)
    db_session.refresh(v2)
    db_session.refresh(job2)
    db_session.refresh(doc)

    # v2 failed
    assert job2.status == "failed"
    assert v2.processing_status == "failed"

    # v1 is still current and completed, document is still active
    assert v1.is_current is True
    assert v1.processing_status == "completed"
    assert doc.status == "active"
