# KnowledgeOps --- Development Backlog

This is an initial sequence. Reorder only when dependencies or new
evidence justify it.

## Epic 1 --- Backend foundation

-   [x] Task 001: Bootstrap FastAPI and health endpoint.

## Epic 2 --- Database foundation

-   [x] Task 002: Establish database foundation (SQLAlchemy, SQLite, Alembic migrations, initial tenant & organizational models, and database tests).
-   [ ] Task 003: Add structured logging and request IDs.
-   [ ] Task 004: Add initial CI/local quality commands.

## Epic 3 --- Identity and authorization

-   [x] Task 009: Decide and implement authentication/session strategy (Bcrypt password hashing, JWT token lifecycle).
-   [x] Task 010: Resolve current user and organization context (`get_current_user`, `get_organization_context`).
-   [x] Task 011: Implement centralized authorization policy and role dependencies (`require_role`, RBAC).
-   [x] Task 012: Add tenant-isolation, membership, and role test suite (25 automated tests verified).

## Epic 4 --- Document management and ingestion

-   [x] Task 013: Implement document metadata models (`Document`, `DocumentVersion`, `DocumentAccessGrant`, `IngestionJob`).
-   [x] Task 014: Implement secure file validation (magic bytes for PDF/DOCX/TXT) and isolated UUID storage.
-   [x] Task 015: Implement upload API, permission filtering, document archiving, and ingestion job creation (18 automated tests).
-   [ ] Task 016: Implement separate SQLite-backed worker.
-   [ ] Task 017: Implement PDF/DOCX/TXT extraction.
-   [ ] Task 018: Implement cleaning and source-aware chunking.
-   [ ] Task 019: Benchmark and select embedding model.
-   [ ] Task 020: Implement embedding provider and Chroma indexing.
-   [ ] Task 021: Add idempotency, retries and index reconciliation.

## Epic 5 --- Retrieval and RAG

-   [ ] Task 022: Implement SQLite FTS5 keyword search.
-   [ ] Task 023: Implement Chroma semantic retrieval.
-   [ ] Task 024: Implement RRF hybrid candidate merge.
-   [ ] Task 025: Implement authorization-before-text-fetch.
-   [ ] Task 026: Implement evidence sufficiency and no-answer behavior.
-   [ ] Task 027: Verify Groq model availability/privacy and select
    model.
-   [ ] Task 028: Implement grounded answer generation.
-   [ ] Task 029: Implement citation validation and persistence.
-   [x] Task 030: Create RAG evaluation dataset and baseline (Single-organization synthetic dataset for Acme Technologies: exactly 20 documents, manifest, 22 evaluation questions, access-control fixtures, and conflict group in `knowledgeops-test-data/`).

## Epic 6 --- Conversations, guardrails and product

-   [ ] Task 031: Implement owner-private conversations.
-   [ ] Task 032: Implement safe follow-up query handling.
-   [ ] Task 033: Add prompt-injection and output validation tests.
-   [ ] Task 034: Add feedback and audit events.
-   [ ] Task 035: Build frontend.
-   [ ] Task 036: Add Docker Compose and deployment.
-   [ ] Task 037: Security, performance and release review.

Do not attempt multiple epics in one coding-agent prompt.
