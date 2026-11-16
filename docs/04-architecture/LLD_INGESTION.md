# KnowledgeOps --- Low-Level Design: Document Ingestion

**Status:** Design baseline; values are provisional until benchmarked.

## 1. Goal

Convert an uploaded supported file into searchable, permission-aware
document chunks while preserving source references and document version
history.

## 2. Supported input

-   PDF
-   DOCX
-   TXT

Reject unsupported, corrupt or invalid files with controlled errors.
Encrypted PDFs are unsupported initially unless a deliberate
password-handling design is approved.

## 3. Processing lifecycle

`pending -> processing -> completed`

Failure path: `processing -> failed -> pending/retry` (or terminal
failed after retry policy is exhausted).

Document lifecycle also supports archived and deleted states. A document
version must not be marked active until processing and indexing are
verified.

## 4. Pipeline

1.  Authenticate and authorize upload.
2.  Validate extension, MIME type, signature/integrity and configured
    size.
3.  Generate a safe storage name; do not trust user-supplied path.
4.  Store original file in local storage.
5.  Create document/version records in SQLite.
6.  Create ingestion job.
7.  Worker claims job using a bounded lease/lock.
8.  Extract text and source locations.
9.  Normalize whitespace and remove extraction noise while preserving
    headings, lists and tables where possible.
10. Split text into structure-aware chunks.
11. Generate embeddings locally.
12. Store chunk text and metadata in SQLite.
13. Upsert vectors and metadata in ChromaDB.
14. Verify expected chunk/vector counts and references.
15. Activate the version and mark job complete.

## 5. Chunking starting hypothesis

Provisional starting point only: - target around 500 tokens; - overlap
around 80 tokens; - minimum around 80 tokens; - maximum around 700
tokens; - preserve headings, paragraph boundaries, page numbers and
section context.

Use a tokenizer appropriate to the selected embedding model. Compare
chunking approaches on a representative dataset before freezing values.
These values are not validated performance claims.

## 6. Chunk metadata

Candidate fields: - chunk_id - organization_id - document_id -
document_version_id - department_id (nullable) - visibility -
chunk_index - page_number (nullable) - section_title (nullable) -
token_count - content_hash - embedding_model_id

Store authoritative chunk text in SQLite. Chroma stores embeddings and
references/metadata needed for retrieval.

## 7. Idempotency and consistency

-   Use deterministic chunk identifiers derived from stable
    document-version identity and chunk index/content strategy.
-   Retrying a job must not create duplicate active chunks.
-   SQLite is authoritative; Chroma is a rebuildable index.
-   If Chroma indexing fails, do not mark the version complete.
-   Keep the previous valid version active until the new version has
    been indexed and verified.
-   Add reconciliation tooling/tests to detect missing or stale vectors.
-   Keep external API/model calls outside long SQLite transactions.

## 8. Worker design

Initial design: a separate Python worker polls/claims jobs from a
SQLite-backed job table. Use a lease/lock so two workers do not process
the same job concurrently. Keep concurrency low initially.

Provisional retry ideas: bounded attempts (for example, three),
exponential backoff with jitter and a lease timeout. Tune after
observing actual failure behavior. Do not add Celery/Redis until
SQLite-backed processing demonstrates a limitation.

## 9. Candidate modules

Create these incrementally as implementation needs them: - document
upload/service/repository/schemas; - file validation and local
storage; - extraction adapters; - text normalization; - chunking; -
ingestion job repository/worker; - embedding provider interface and
Hugging Face adapter; - vector-store interface and Chroma adapter.

Do not generate all folders in advance.

## 10. Tests

-   Valid PDF/DOCX/TXT accepted.
-   Unsupported extension and mismatched file signature rejected.
-   Corrupt file fails safely.
-   Extracted text preserves available page/section references.
-   Chunk metadata references correct document version.
-   Embedding failure is retryable.
-   Chroma failure does not activate version.
-   Retry does not create duplicate active chunks.
-   Old active version remains available while new version is
    processing.
-   Unauthorized uploader is rejected.
