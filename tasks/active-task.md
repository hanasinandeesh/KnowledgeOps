# Active Task --- Task 004: Document Management & Upload APIs

**Status:** Completed and verified.\
**Environment:** Antigravity + Gemini.\
**Working Python version:** 3.11.

## Objective

Implement secure document management and file upload APIs with file content validation (PDF, DOCX, TXT), safe local filesystem persistence, tenant and visibility isolation, document listing with permission filtering, and document archiving for KnowledgeOps.

## Scope

-   Update `backend/pyproject.toml` and `requirements.txt` with `python-multipart>=0.0.9`.
-   Update `backend/app/core/config.py` with `DOCUMENT_STORAGE_PATH`, `MAX_FILE_SIZE_BYTES`, and `ALLOWED_EXTENSIONS`.
-   Update `backend/app/core/exceptions.py` with `PayloadTooLargeException` (HTTP 413) and `UnsupportedMediaTypeException` (HTTP 415).
-   Implement file validator in `backend/app/modules/documents/validator.py` (extension, size, and magic-byte checks for PDF `%PDF-`, DOCX ZIP package with `[Content_Types].xml`, and TXT non-binary UTF-8).
-   Implement local storage service in `backend/app/modules/documents/storage.py` with UUID storage filenames and cleanup on failure.
-   Implement SQLAlchemy models in `backend/app/models/document.py` (`Document`, `DocumentVersion`, `DocumentAccessGrant`, `IngestionJob`).
-   Generate and execute Alembic batch migration `366b3ef58924_document_and_ingestion_models.py`.
-   Implement Pydantic schemas in `backend/app/modules/documents/schemas.py`.
-   Implement business logic and authorization in `backend/app/modules/documents/service.py`:
    -   Upload authorization rules (organization, department, restricted).
    -   Transactional write and disk file rollback cleanup.
    -   Permission-aware document listing and details retrieval.
    -   Document archiving lifecycle.
-   Implement FastAPI routes in `backend/app/modules/documents/router.py`:
    -   `POST /api/v1/documents`
    -   `GET /api/v1/documents`
    -   `GET /api/v1/documents/{document_id}`
    -   `POST /api/v1/documents/{document_id}/archive`
-   Register `documents_router` in `backend/app/main.py`.
-   Implement automated test suite in `backend/tests/test_documents.py` (18 comprehensive test cases).
-   Verify all 43 tests pass and `ruff check backend` passes with 0 errors.

## Explicitly out of scope

-   Ingestion background worker processes, text extraction, cleaning, and chunking (Task 005 / Epic 4).
-   ChromaDB vector store and embeddings (Epic 4 / 5).
-   SQLite FTS5 full-text search indexing (Epic 5).
-   Frontend or Docker Compose.

## Acceptance criteria

-   [x] `python-multipart>=0.0.9` added to dependencies.
-   [x] Configuration updated with storage paths and size limits.
-   [x] File validator checks magic bytes for PDF, DOCX, and TXT, rejecting spoofed, corrupt, or empty files.
-   [x] Uploaded files stored outside web roots using safe UUID filenames; raw user paths never used on disk.
-   [x] Internal storage paths and file hashes are never exposed in API client responses.
-   [x] Multipart upload creates `Document`, `DocumentVersion`, and `IngestionJob` returning HTTP 202 `Accepted`.
-   [x] Organization-wide, department-specific, and restricted visibility rules enforced on the backend.
-   [x] Organization admin does not automatically gain access to restricted documents without an explicit grant.
-   [x] Document listing applies server-side permission filtering.
-   [x] Document archiving updates status and excludes document from active retrieval.
-   [x] Database failure during upload cleans up disk files without leaving orphaned files or rows.
-   [x] Comprehensive test suite created (`test_documents.py`) and all 43 backend tests pass.
-   [x] `ruff check backend` passes cleanly with 0 errors.
-   [x] Documentation and `CURRENT_STATUS.md` updated.
