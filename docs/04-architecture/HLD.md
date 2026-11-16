# KnowledgeOps --- High-Level Design (HLD)

**Status:** Design baseline; not implemented.

## 1. Architecture style

Use a modular monolith. One backend application contains clearly
separated modules. A separate Python worker handles document ingestion
jobs initially.

Do not start with microservices, Redis, Kafka or Kubernetes.

## 2. Logical components

-   API layer: FastAPI routes, request validation and response schemas.
-   Core: configuration, authentication context, shared errors and
    logging.
-   Auth/organization modules: users, memberships, roles and tenant
    context.
-   Document module: metadata, versions, visibility and upload.
-   Ingestion module: job lifecycle and processing orchestration.
-   Extraction/cleaning/chunking: convert source files into structured
    chunks.
-   Embedding provider: local Hugging Face model.
-   Vector-store adapter: ChromaDB.
-   Retrieval module: semantic + keyword search, candidate merging and
    authorization filtering.
-   RAG module: evidence assembly, prompt construction, Groq generation
    and answer validation.
-   Conversation module: private conversations and message history.
-   Feedback/audit modules: user feedback and security-relevant events.
-   Infrastructure: SQLite persistence, local file storage and worker
    process.

## 3. Technology baseline

  Concern                Initial choice
  ---------------------- ---------------------------------------
  API                    FastAPI
  Language               Python; 3.12 is the working candidate
  Application database   SQLite
  ORM/migrations         SQLAlchemy / Alembic (proposed)
  Vector store           ChromaDB
  Embeddings             Hugging Face local model
  LLM                    Groq API
  Keyword search         SQLite FTS5
  RAG integration        LangChain
  Stateful workflow      LangGraph selectively
  Tests                  Pytest
  Evaluation             RAGAS planned
  Local environment      Docker Compose planned

Exact library versions and model identifiers must be verified at
implementation time.

## 4. Ingestion architecture

1.  Authenticated user uploads file.
2.  API validates user permission and file.
3.  Original file is stored locally using a generated safe name.
4.  SQLite stores document/version metadata and an ingestion job.
5.  Separate worker claims a job.
6.  Worker extracts, cleans and chunks text.
7.  Worker generates local embeddings.
8.  Worker persists authoritative chunks in SQLite.
9.  Worker indexes vectors and metadata in ChromaDB.
10. Worker verifies consistency and activates the version.
11. Job and document status are updated.

Do not hold an HTTP request open while extracting and embedding a large
document.

## 5. Query architecture

1.  Authenticate user and derive organization context server-side.
2.  Validate question and load conversation context if applicable.
3.  Create query embedding.
4.  Search ChromaDB for semantic candidates.
5.  Search SQLite FTS5 for keyword candidates.
6.  Merge/deduplicate candidates using Reciprocal Rank Fusion (RRF).
7.  Validate candidate document permissions and lifecycle in SQLite.
8.  Fetch authoritative chunk text only for authorized candidates.
9.  Assess evidence sufficiency and assemble context.
10. Call Groq with constrained instructions and authorized evidence
    only.
11. Validate response structure and citations.
12. Persist conversation/message/source references.
13. Return answer and citations.

## 6. Data ownership

SQLite is authoritative for: - organizations, users, memberships and
roles; - departments and department membership; - documents and
versions; - access grants and lifecycle state; - chunk text and source
metadata; - jobs, conversations, messages, feedback and audit events.

ChromaDB stores vectors and retrieval metadata. It is rebuildable and is
not the source of truth for permissions or content.

Local filesystem stores original uploaded files.

## 7. Deployment topology for MVP

Initial local setup: - FastAPI process. - Separate ingestion worker
process. - SQLite database file. - ChromaDB local persistent storage. -
Local document storage directory. - Groq external API calls. - Local
Hugging Face embedding model.

Docker Compose may be used to make local setup reproducible. Avoid
introducing separate infrastructure services unless needed.

## 8. API groups

-   `/api/v1/auth`
-   `/api/v1/users`
-   `/api/v1/organizations`
-   `/api/v1/documents`
-   `/api/v1/ingestion-jobs`
-   `/api/v1/search`
-   `/api/v1/conversations`
-   `/api/v1/feedback`

See `docs/api/API_CONTRACTS.md` for initial contracts.

## 9. Important constraints

-   Tenant identity is server-derived.
-   Authorization is checked before source text enters model context.
-   Chroma filters are defense in depth only.
-   New document versions are not active until fully indexed.
-   External LLM receives retrieved document content; use synthetic
    documents until provider privacy terms are reviewed.
-   No shared answer cache in MVP.
-   Provider model names and free-tier limits are not frozen.
