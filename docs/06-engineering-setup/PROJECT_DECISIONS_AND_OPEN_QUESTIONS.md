# KnowledgeOps --- Decisions and Open Questions

Use this file to distinguish confirmed decisions from proposals. Do not
silently promote a proposal to a confirmed decision.

## 1. Confirmed by product/design discussions

-   Product name: KnowledgeOps.
-   Product category: Enterprise Knowledge Intelligence Platform.
-   Deployment scope: Dedicated single-organization enterprise system (internal company platform for one organization, rather than a multi-tenant public SaaS).
-   Primary user: employee.
-   Initial customer assumption: mid-sized organizations; approximately
    100--1,000 employees as a planning segment.
-   MVP purpose: secure knowledge discovery from uploaded company
    documents.
-   MVP formats: PDF, DOCX, TXT.
-   Initial ingestion: manual uploads.
-   Document scopes: organization-wide, department-specific, restricted.
-   Conversations private by default.
-   Organization-wide documents are visible only within the same tenant
    to authorized users.
-   Organization-wide upload is restricted to admins and authorized
    HR/department managers.
-   Backend authorization is mandatory before text enters LLM context.
-   SQLite is initial application database.
-   ChromaDB is initial vector store.
-   Hugging Face embeddings run locally.
-   Groq is initial LLM provider.
-   Hybrid retrieval uses Chroma semantic search plus SQLite FTS5
    keyword search with RRF.
-   Modular monolith.
-   Separate Python worker with SQLite-backed jobs initially.
-   LangChain for useful integrations; LangGraph selectively.
-   No shared answer cache in MVP.
-   Use synthetic documents while external provider privacy handling is
    not approved.

## 2. Proposed implementation choices

These are sensible starting proposals, not yet immutable: - SQLAlchemy
for ORM. - Alembic for migrations. - Python 3.12. - Ruff for
lint/format. - Pytest and HTTPX for tests. - Docker Compose for
reproducible local setup. - Local filesystem for original document
storage. - A bounded worker lease and retry policy. - RRF constant
around 60 as an initial experiment. - Chunk target around 500 tokens and
overlap around 80 tokens as an initial experiment.

## 3. Open decisions

1.  Exact Hugging Face embedding model: benchmark MiniLM and BGE-small
    candidates.
2.  Exact Groq model: verify current availability, rate limits, context
    window, quality and terms.
3.  Exact package versions and dependency lock strategy.
4.  Frontend framework and UI design.
5.  Authentication/session/token mechanism.
6.  Upload size and parser resource limits.
7.  Final chunking parameters.
8.  Retrieval candidate counts and context size.
9.  Evidence sufficiency and no-answer thresholds.
10. Source authority precedence when documents conflict.
11. Document deletion, retention and backup policy.
12. Historical conversation behavior after permission revocation.
13. Production deployment platform and object storage.
14. Malware scanning approach before production.
15. Numeric performance and quality targets after baseline evaluation.

## 4. Decision process

When an open decision blocks implementation: 1. Explain the decision and
why it matters. 2. Offer a small set of options with trade-offs. 3. Ask
the user to approve one. 4. Record the outcome in the relevant design
document and ADR. 5. Do not silently choose a costly or
security-sensitive option.
