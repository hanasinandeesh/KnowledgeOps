import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.models.document import (
    Document,
    DocumentChunk,
    DocumentPage,
    DocumentVersion,
    IngestionJob,
)
from app.models.organization import Organization
from app.models.user import User
from app.modules.documents.storage import DocumentStorageService
from app.modules.indexing.embeddings import DeterministicMockEmbeddingProvider
from app.modules.indexing.schemas import IndexingError
from app.modules.indexing.service import IndexingService
from app.modules.indexing.vector_store import ChromaVectorStore
from app.modules.ingestion.worker import IngestionWorker


def create_pipeline_test_doc(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    version_number: int = 1,
    existing_doc_id: str | None = None,
) -> tuple[Document, DocumentVersion, IngestionJob]:
    """Helper to save a physical document file and record Document, Version, and Job."""
    doc_id = existing_doc_id or str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

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


def test_end_to_end_worker_chunking_and_indexing(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    tmp_path: Path,
) -> None:
    """Worker extracts pages, chunks text, persists chunks, and indexes vectors."""
    content = (
        "# Section 1: Travel Policy\n"
        "Employees must book standard economy flights for domestic trips.\n\n"
        "# Section 2: Meal Allowances\n"
        "Daily meal allowance is capped at $75 per day with itemized receipts."
    )
    doc, version, job = create_pipeline_test_doc(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=content.encode("utf-8"),
        filename="travel_policy.txt",
        mime_type="text/plain",
    )

    chroma_store = ChromaVectorStore(
        persist_path=tmp_path / "chroma_e2e",
        collection_name="test_e2e_chunks",
    )
    mock_embeddings = DeterministicMockEmbeddingProvider(dimension=384)
    indexing_service = IndexingService(
        embedding_provider=mock_embeddings,
        vector_store=chroma_store,
    )

    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="pipeline-worker-1",
        session_factory=session_factory,
        indexing_service=indexing_service,
    )

    did_work = worker.process_one_job()
    assert did_work is True

    db_session.refresh(job)
    db_session.refresh(version)
    db_session.refresh(doc)

    # 1. State assertions
    assert job.status == "completed"
    assert version.processing_status == "completed"
    assert version.is_current is True
    assert doc.status == "active"

    # 2. SQLite DocumentPages assertions
    pages = (
        db_session.query(DocumentPage)
        .filter(DocumentPage.document_version_id == version.id)
        .all()
    )
    assert len(pages) == 2

    # 3. SQLite DocumentChunks assertions
    chunks = (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.document_version_id == version.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].section_title == "Section 1: Travel Policy"
    assert "economy flights" in chunks[0].content
    assert chunks[0].token_count > 0
    assert len(chunks[0].content_hash) == 64

    assert chunks[1].chunk_index == 1
    assert chunks[1].section_title == "Section 2: Meal Allowances"
    assert "$75 per day" in chunks[1].content

    # 4. ChromaDB assertions
    assert chroma_store.count_by_version(version.id) == len(chunks)
    assert chroma_store.get_collection_count() == len(chunks)


def test_version_transition_deactivates_old_version(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    tmp_path: Path,
) -> None:
    """When Version 2 succeeds, Version 1 is marked is_current=False and V2 active."""
    chroma_store = ChromaVectorStore(
        persist_path=tmp_path / "chroma_v_transition",
        collection_name="test_v_transition",
    )
    mock_embeddings = DeterministicMockEmbeddingProvider(dimension=384)
    indexing_service = IndexingService(
        embedding_provider=mock_embeddings,
        vector_store=chroma_store,
    )
    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="v-worker",
        session_factory=session_factory,
        indexing_service=indexing_service,
    )

    # 1. Ingest Version 1
    doc, v1, job1 = create_pipeline_test_doc(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Version 1 text content.",
        filename="policy_v1.txt",
        mime_type="text/plain",
        version_number=1,
    )
    assert worker.process_one_job() is True
    db_session.refresh(v1)
    assert v1.is_current is True
    assert v1.processing_status == "completed"
    assert chroma_store.count_by_version(v1.id) == 1

    # 2. Ingest Version 2
    _, v2, job2 = create_pipeline_test_doc(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Version 2 updated policy text.",
        filename="policy_v2.txt",
        mime_type="text/plain",
        version_number=2,
        existing_doc_id=doc.id,
    )
    assert worker.process_one_job() is True
    db_session.refresh(v1)
    db_session.refresh(v2)

    # V2 is now current, V1 is superseded
    assert v2.is_current is True
    assert v2.processing_status == "completed"
    assert v1.is_current is False
    assert v1.processing_status == "completed"

    # Both versions exist in SQLite for version history
    v1_chunks = (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.document_version_id == v1.id)
        .count()
    )
    v2_chunks = (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.document_version_id == v2.id)
        .count()
    )
    assert v1_chunks == 1
    assert v2_chunks == 1

    # Stale V1 vectors purged from ChromaDB; only V2 vectors remain
    assert chroma_store.count_by_version(v1.id) == 0
    assert chroma_store.count_by_version(v2.id) == 1
    assert chroma_store.get_collection_count() == 1


def test_failed_v2_leaves_v1_active_and_purges_v2_vectors(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    tmp_path: Path,
) -> None:
    """When Version 2 fails, Version 1 remains current and V2 vectors are wiped."""
    chroma_store = ChromaVectorStore(
        persist_path=tmp_path / "chroma_fail_v2",
        collection_name="test_fail_v2",
    )
    mock_embeddings = DeterministicMockEmbeddingProvider(dimension=384)
    indexing_service = IndexingService(
        embedding_provider=mock_embeddings,
        vector_store=chroma_store,
    )
    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="v-worker",
        session_factory=session_factory,
        indexing_service=indexing_service,
    )

    # 1. Ingest valid V1
    doc, v1, job1 = create_pipeline_test_doc(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"Valid V1 text",
        filename="v1.txt",
        mime_type="text/plain",
        version_number=1,
    )
    assert worker.process_one_job() is True
    db_session.refresh(v1)
    assert v1.is_current is True

    # 2. Upload corrupt V2
    _, v2, job2 = create_pipeline_test_doc(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"%PDF-corrupt trash data",
        filename="v2.pdf",
        mime_type="application/pdf",
        version_number=2,
        existing_doc_id=doc.id,
    )
    assert worker.process_one_job() is True
    db_session.refresh(v1)
    db_session.refresh(v2)
    db_session.refresh(job2)

    # V2 failed
    assert job2.status == "failed"
    assert v2.processing_status == "failed"
    assert chroma_store.count_by_version(v2.id) == 0

    # V1 remains active and untouched
    assert v1.is_current is True
    assert v1.processing_status == "completed"
    assert doc.status == "active"
    assert chroma_store.count_by_version(v1.id) == 1


def test_embedding_failure_retries_and_recovers_without_duplicates(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    tmp_path: Path,
) -> None:
    """Transient embedding failure retries cleanly without leaving duplicate chunks."""

    class FlakyEmbeddingProvider(DeterministicMockEmbeddingProvider):
        def __init__(self) -> None:
            super().__init__(dimension=384)
            self.calls = 0

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            self.calls += 1
            if self.calls == 1:
                raise IndexingError(
                    "Simulated transient CPU OOM",
                    code="EMBEDDING_GENERATION_ERROR",
                )
            return super().embed_documents(texts)

    content = "# Section A\nFirst policy section.\n\n# Section B\nSecond section."
    doc, version, job = create_pipeline_test_doc(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=content.encode("utf-8"),
        filename="flaky.txt",
        mime_type="text/plain",
    )

    chroma_store = ChromaVectorStore(
        persist_path=tmp_path / "chroma_retry",
        collection_name="test_retry_chunks",
    )
    flaky_provider = FlakyEmbeddingProvider()
    indexing_service = IndexingService(
        embedding_provider=flaky_provider,
        vector_store=chroma_store,
    )
    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="retry-worker",
        session_factory=session_factory,
        indexing_service=indexing_service,
    )

    # Attempt 1 fails with retryable embedding error
    assert worker.process_one_job() is True
    db_session.refresh(job)
    db_session.refresh(version)
    assert job.status == "pending"
    assert job.attempts == 1
    assert job.last_error_code == "EMBEDDING_GENERATION_ERROR"
    assert job.next_retry_at is not None
    assert chroma_store.count_by_version(version.id) == 0

    # Fast-forward backoff timer so Attempt 2 can run immediately
    job.next_retry_at = datetime.now(timezone.utc)
    db_session.commit()

    # Attempt 2 succeeds with exact 1:1 SQLite chunks and Chroma vectors
    assert worker.process_one_job() is True
    db_session.refresh(job)
    db_session.refresh(version)
    db_session.refresh(doc)

    assert job.status == "completed"
    assert job.attempts == 2
    assert version.processing_status == "completed"
    assert doc.status == "active"

    sqlite_chunk_count = (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.document_version_id == version.id)
        .count()
    )
    assert sqlite_chunk_count == 2
    assert chroma_store.count_by_version(version.id) == 2
    assert chroma_store.get_collection_count() == 2


def test_chroma_count_mismatch_purges_partial_vectors_and_retries(
    db_session: Session,
    test_user: User,
    test_org: Organization,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Count mismatch between SQLite chunks and ChromaDB purges vectors and retries."""
    doc, version, job = create_pipeline_test_doc(
        db_session=db_session,
        test_user=test_user,
        test_org=test_org,
        file_bytes=b"# Heading\nSome policy text for consistency check.",
        filename="mismatch.txt",
        mime_type="text/plain",
    )

    chroma_store = ChromaVectorStore(
        persist_path=tmp_path / "chroma_mismatch",
        collection_name="test_mismatch_chunks",
    )
    real_count = chroma_store.count_by_version

    # Force verification count check to report 0 instead of 1
    monkeypatch.setattr(chroma_store, "count_by_version", lambda _vid: 0)

    indexing_service = IndexingService(
        embedding_provider=DeterministicMockEmbeddingProvider(dimension=384),
        vector_store=chroma_store,
    )
    session_factory = sessionmaker(bind=db_session.get_bind())
    worker = IngestionWorker(
        worker_id="mismatch-worker",
        session_factory=session_factory,
        indexing_service=indexing_service,
    )

    assert worker.process_one_job() is True
    db_session.refresh(job)
    db_session.refresh(version)
    db_session.refresh(doc)

    assert job.status == "pending"
    assert job.last_error_code == "INDEXING_COUNT_MISMATCH"
    assert version.processing_status == "processing"
    assert doc.status == "pending"

    # Partial vectors written before mismatch check must be purged from ChromaDB
    assert real_count(version.id) == 0
    assert (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.document_version_id == version.id)
        .count()
        == 0
    )
