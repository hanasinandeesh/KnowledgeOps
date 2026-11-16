# KnowledgeOps --- Architecture Decision Records

This file records the current decision baseline. A decision may be
revised through an explicit, documented change.

## ADR-001: Modular monolith

**Status:** Confirmed design direction.\
**Decision:** Build one modular backend application with clear domain
boundaries.\
**Reason:** Keeps MVP operational complexity low while supporting
maintainable modules.\
**Revisit when:** Deployment, team ownership or scaling requirements
demonstrate a real need for service separation.

## ADR-002: SQLite initially

**Status:** Confirmed initial choice.\
**Decision:** Use SQLite as the initial application database and source
of truth.\
**Reason:** Simple local development and low operational overhead.\
**Constraints:** Use migrations, enforce foreign keys, keep transactions
short and test concurrency behavior. PostgreSQL migration is a later
planned step, not a config-only change.

## ADR-003: ChromaDB vector store

**Status:** Confirmed initial choice.\
**Decision:** Use ChromaDB for vector retrieval.\
**Reason:** Suitable for local MVP experimentation.\
**Constraints:** Chroma is a rebuildable index, not the authority for
permissions or chunk content.

## ADR-004: Local Hugging Face embeddings

**Status:** Confirmed provider approach; model open.\
**Decision:** Run embeddings locally using a Hugging Face
sentence-transformer model.\
**Candidates:** `sentence-transformers/all-MiniLM-L6-v2` and
`BAAI/bge-small-en-v1.5`.\
**Open:** Benchmark both on the KnowledgeOps dataset before selecting.
Model changes require re-embedding and index rebuild.

## ADR-005: Groq initial LLM provider

**Status:** Confirmed provider direction; exact model open.\
**Decision:** Use Groq API for initial answer generation.\
**Open:** Verify current model availability, limits, context window,
quality and provider data-handling terms at implementation time. Do not
assume unlimited free use.

## ADR-006: Separate Python ingestion worker

**Status:** Confirmed design direction.\
**Decision:** Use SQLite-backed ingestion jobs and a separate Python
worker initially.\
**Reason:** Avoid long-running document processing inside HTTP requests
without introducing distributed infrastructure prematurely.

## ADR-007: Hybrid retrieval

**Status:** Confirmed design direction.\
**Decision:** Combine Chroma semantic retrieval and SQLite FTS5 keyword
retrieval using RRF.\
**Open:** Candidate counts, score thresholds and final context size
require evaluation.

## ADR-008: Backend-enforced authorization

**Status:** Mandatory confirmed rule.\
**Decision:** Validate tenant and document permissions in backend/SQLite
before fetching chunk text for model context.\
**Reason:** Vector metadata filters cannot be trusted as the security
boundary.

## ADR-009: LangChain and selective LangGraph

**Status:** Confirmed design direction.\
**Decision:** Use LangChain where it simplifies retrieval/model
integration. Use LangGraph only for stateful/branching workflows where
justified.\
**Constraint:** Do not introduce graph orchestration into simple
endpoints.

## ADR-010: Local Docker Compose development

**Status:** Accepted initial direction.\
**Decision:** Use Docker Compose when needed for reproducible local
application/worker setup.\
**Constraint:** Do not add unnecessary services such as Redis or Kafka
in MVP.

## ADR-011: Local files for original documents

**Status:** Initial design baseline.\
**Decision:** Store original uploaded documents on local filesystem in
MVP.\
**Open:** Production object storage and retention strategy are future
decisions.

## ADR-012: No shared answer cache in MVP

**Status:** Security baseline.\
**Decision:** Do not introduce shared answer caching until
authorization-aware invalidation and revalidation are designed and
tested.
