# Active Task --- Task 006: Embeddings & Vector Indexing

**Status:** Completed and verified.\
**Environment:** Antigravity + Gemini.\
**Working Python version:** 3.11.

## Objective

Transform successfully extracted document pages from Task 005 into structure-aware text chunks and vector embeddings, stored authoritatively in SQLite (`document_chunks`) and indexed in a persistent local ChromaDB instance, with atomic version transitions and safe error recovery.

## Scope

-   Update `backend/requirements.txt` and `backend/pyproject.toml` with `sentence-transformers>=3.0.0` and `chromadb>=0.5.0`.
-   Update `backend/app/core/config.py` with indexing configurations:
    -   `CHROMA_PERSISTENCE_PATH` (default: `./data/chroma`)
    -   `CHROMA_COLLECTION_NAME` (default: `knowledgeops_chunks`)
    -   `EMBEDDING_MODEL_ID` (default: `BAAI/bge-small-en-v1.5`)
    -   `EMBEDDING_CACHE_DIR` (default: `./data/models/embeddings`)
    -   `CHUNK_TARGET_TOKENS` (default: 500)
    -   `CHUNK_OVERLAP_TOKENS` (default: 80)
    -   `CHUNK_MIN_TOKENS` (default: 80)
    -   `CHUNK_MAX_TOKENS` (default: 700)
-   Update `backend/app/models/document.py` and `backend/app/models/__init__.py`:
    -   Define `DocumentChunk` model (`document_chunks` table) with foreign keys, indexes, and unique constraint `(document_version_id, chunk_index)`.
    -   Establish relationship between `DocumentVersion` and `DocumentChunk`.
-   Generate and execute Alembic batch migration `661098a376d0_document_chunks_model.py`.
-   Implement indexing architecture under `backend/app/modules/indexing/`:
    -   `schemas.py`: `TextChunk`, `ChunkMetadata`, `IndexingResult`, and `IndexingError`.
    -   `chunker.py`: `TextChunker` with structure-aware hierarchical splitting (headings -> paragraphs -> sentences), contextual section prefixing, exact token counting, and small trailing chunk merging.
    -   `embeddings.py`: `BaseEmbeddingProvider`, `LocalSentenceTransformerEmbedding` (lazy model initialization, normalized embeddings, CPU execution), and `DeterministicMockEmbeddingProvider`.
    -   `vector_store.py`: `BaseVectorStore`, `ChromaVectorStore` (persistent client, cosine distance metric, batched upsert, version deletion, count verification).
    -   `service.py`: `IndexingService` coordinating chunk generation, embedding, ChromaDB upsert, verification, and vector purging.
-   Integrate indexing into `JobQueueService` and `IngestionWorker`:
    -   Step 1: Claim job (atomic SQLite lease).
    -   Step 2: Extract content outside DB locks.
    -   Step 3: Persist extracted pages in SQLite.
    -   Step 4: Chunk, embed, and index into ChromaDB via `IndexingService` outside DB locks.
    -   Step 5: Persist `DocumentChunk` records, activate current version, deactivate older versions, mark document active, and complete job.
    -   On failure: purge partial version vectors from ChromaDB and schedule retry or mark failed without touching previous active version.
-   Implement comprehensive test suites:
    -   `backend/tests/test_chunker.py` (5 unit tests).
    -   `backend/tests/test_embeddings.py` (4 unit tests).
    -   `backend/tests/test_vector_store.py` (5 unit tests, including restart persistence).
    -   `backend/tests/test_indexing_pipeline.py` (5 end-to-end integration tests, including stale V1 vector cleanup on V2 activation, embedding retry recovery without duplicates, and Chroma count-mismatch recovery).
-   Configure editable backend packaging (`[build-system]` and `[tool.setuptools.packages.find]` in `backend/pyproject.toml`, `prepend_sys_path = %(here)s` in `backend/alembic.ini`) so `app` imports cleanly from any working directory.
-   Verify all 91 backend tests pass with 0 warnings and `ruff check backend` / `ruff format --check backend` pass with 0 errors.

## Acceptance criteria

- [x] `sentence-transformers>=3.0.0` and `chromadb>=0.5.0` added to dependencies.
- [x] Alembic migration `661098a376d0_document_chunks_model.py` applied.
- [x] Text chunking preserves page numbers, section titles, and hierarchical headers.
- [x] Local embeddings generated using 384-dimensional model (`BAAI/bge-small-en-v1.5`).
- [x] ChromaDB persists vectors to disk with deterministic chunk IDs.
- [x] SQLite remains authoritative source for document and chunk metadata.
- [x] Complete worker pipeline links extraction -> chunking -> embedding -> indexing -> verification -> activation -> stale version vector purge.
- [x] Ingestion failure of a new version leaves the active version untouched and cleans up orphaned vectors.
- [x] All 91 backend tests pass with 0 warnings.
- [x] `ruff check backend` and `ruff format --check backend` pass cleanly with 0 errors.
