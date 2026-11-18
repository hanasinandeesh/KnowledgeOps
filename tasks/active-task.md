# Active Task --- Task 005: Document Ingestion Worker & Text Extraction

**Status:** Completed and verified.\
**Environment:** Antigravity + Gemini.\
**Working Python version:** 3.11.

## Objective

Implement a robust, asynchronous background document ingestion worker that safely claims pending jobs from SQLite using atomic leases, extracts and normalizes text from PDF, DOCX, and TXT files, preserves page and section structure in `document_pages`, handles malformed or encrypted documents with controlled errors, and enforces bounded exponential backoff retries without corrupting active document versions.

## Scope

-   Update `backend/requirements.txt` and `backend/pyproject.toml` with `pymupdf>=1.24.0` and `python-docx>=1.1.0`.
-   Update `backend/app/core/config.py` with worker configuration settings:
    -   `WORKER_POLL_INTERVAL_SECONDS` (default: 2.0s)
    -   `WORKER_LEASE_SECONDS` (default: 120s)
    -   `WORKER_MAX_ATTEMPTS` (default: 3)
    -   `WORKER_BASE_BACKOFF_SECONDS` (default: 5s)
-   Update `backend/app/models/document.py`:
    -   Define `DocumentPage` model (`document_pages` table) with composite uniqueness on `(document_version_id, page_number, id)`.
    -   Add `next_retry_at` and `last_error_message` to `IngestionJob`.
    -   Establish relationship between `DocumentVersion` and `DocumentPage`.
-   Generate and execute Alembic batch migration `fc94e6e785cc_ingestion_worker_and_pages.py`.
-   Implement extraction architecture under `backend/app/modules/ingestion/`:
    -   `schemas.py`: `ExtractedPage`, `ExtractedDocument`, and `DocumentExtractionError`.
    -   `cleaner.py`: `TextCleaner.normalize` (NFKC normalization, control character stripping, excessive newline collapsing, line whitespace trimming) and `validate_non_empty`.
    -   `extractors/base.py`: Abstract `BaseExtractor` interface.
    -   `extractors/pdf.py`: `PyMuPDFExtractor` with per-page text extraction, page number preservation, and encrypted PDF detection.
    -   `extractors/docx.py`: `DocxExtractor` using `python-docx` iterating through body elements in sequential order, extracting headings (`Heading 1`/`Heading 2`), paragraphs, and formatted table rows.
    -   `extractors/txt.py`: `TxtExtractor` with UTF-8 validation and Markdown heading section splitting.
    -   `extractors/factory.py`: `ExtractorFactory` with MIME-type and extension-based dispatch.
    -   `job_queue.py`: `JobQueueService` with race-free atomic SQLite job claiming, lease renewals, crash recovery, page persistence, version activation, and exponential backoff retry scheduling.
    -   `worker.py`: `IngestionWorker` standalone polling loop, transaction boundary isolation (no DB locks during file reading/extraction), and graceful shutdown on `SIGINT`/`SIGTERM`.
-   Implement comprehensive test suites:
    -   `backend/tests/test_text_cleaner.py` (6 unit tests).
    -   `backend/tests/test_extractors.py` (13 unit tests covering PDF, DOCX, TXT, corrupt files, blank files, password-protected PDFs, and factory dispatch).
    -   `backend/tests/test_ingestion_worker.py` (10 integration tests covering atomic claiming, concurrency prevention, lease recovery, backoff delays, end-to-end TXT/PDF extraction, terminal failure, retry backoff, max retries, and version preservation).
-   Verify all 72 backend tests pass and `ruff check backend` / `ruff format --check backend` pass with 0 errors.

## Explicitly out of scope

-   Chunking into retrieval chunks and token counting (Task 018).
-   Local embedding generation and ChromaDB vector indexing (Task 019/020).
-   Hybrid search (Epic 5).
-   Frontend or Docker Compose.

## Acceptance criteria

-   [x] `pymupdf>=1.24.0` and `python-docx>=1.1.0` added to dependencies.
-   [x] Alembic migration `fc94e6e785cc_ingestion_worker_and_pages.py` applied.
-   [x] Text extractors extract text and preserve page numbers for PDF and headings/sections for DOCX and TXT.
-   [x] Malformed, corrupt, or encrypted documents are rejected with descriptive, controlled error codes (`CORRUPTED_DOCUMENT`, `ENCRYPTED_PDF`, `EMPTY_EXTRACTED_CONTENT`).
-   [x] Text normalizer cleans text without altering semantic meaning or headings.
-   [x] Empty extracted content (0 characters or all whitespace) is treated as a controlled failure.
-   [x] Worker runs as a separate process and safely claims jobs using atomic SQLite updates without race conditions.
-   [x] Expired worker leases are automatically recovered.
-   [x] Bounded retries (3 attempts) with exponential backoff are enforced for transient errors.
-   [x] Database transactions are kept short and never held open during document file parsing.
-   [x] Ingestion failure of a new version preserves the previous active version without data loss.
-   [x] All 72 backend tests pass.
-   [x] `ruff check backend` and `ruff format --check backend` pass cleanly with 0 errors.
