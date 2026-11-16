# KnowledgeOps --- Requirements Baseline

**Status:** Product discovery baseline finalized; implementation not yet
verified.

## 1. Scope assumptions

-   Initial customer segment: mid-sized organizations.
-   Primary user: employee.
-   Initial ingestion: manual upload only.
-   Formats: PDF, DOCX, TXT.
-   Conversations private by default.
-   Knowledge discovery only; no workflow execution.
-   Guardrails and permission-aware retrieval are mandatory MVP
    requirements.

## 2. Functional requirements

### Identity and organization

-   FR-001: Users must authenticate before accessing protected
    application functions.
-   FR-002: The system must associate users with organizations through
    memberships.
-   FR-003: The system must support employee, department manager and
    organization admin roles.
-   FR-004: Tenant identity must be derived from trusted server-side
    authentication context.
-   FR-005: Organization-owned data must be isolated by tenant.
-   FR-006: User and membership status changes must affect subsequent
    access checks.

### Document management

-   FR-007: Authorized users must upload PDF, DOCX and TXT documents.
-   FR-008: The system must validate extension, MIME type, file
    signature/integrity and configured size limits.
-   FR-009: The system must store original files using safe generated
    storage names.
-   FR-010: The system must store document metadata and uploader
    identity.
-   FR-011: Documents must support organization-wide,
    department-specific and restricted visibility.
-   FR-012: Organization-wide uploads must be limited to admins and
    authorized HR/department managers according to configured policy.
-   FR-013: Department uploads must be permission-checked.
-   FR-014: Restricted documents must support explicit user or role
    grants.
-   FR-015: The system must expose document processing status and
    controlled errors.

### Ingestion and indexing

-   FR-016: The system must extract text from supported file formats.
-   FR-017: The system must normalize extracted text without destroying
    meaningful structure.
-   FR-018: Chunking must preserve source references such as document
    version, page and section where available.
-   FR-019: The system must generate embeddings using the configured
    local embedding provider.
-   FR-020: Authoritative chunk text and metadata must be stored in
    SQLite.
-   FR-021: ChromaDB must store vectors and references/metadata needed
    for candidate retrieval.
-   FR-022: Ingestion must use background jobs rather than long-running
    in-process HTTP work.
-   FR-023: Jobs must be retryable and idempotent.
-   FR-024: A new document version must not become active until
    processing and indexing are verified.

### Retrieval and RAG

-   FR-025: Users must be able to search authorized knowledge.
-   FR-026: The system must support semantic retrieval.
-   FR-027: The system must support keyword retrieval.
-   FR-028: The system must combine retrieval candidates using a
    documented hybrid strategy.
-   FR-029: Retrieval must consider tenant, visibility, department,
    grants, lifecycle and version state.
-   FR-030: Backend authorization must be checked before chunk text is
    fetched for LLM context.
-   FR-031: The system must avoid duplicate evidence chunks.
-   FR-032: Reranking may be introduced after evaluation demonstrates
    value; it is not required in the first retrieval slice.

### Answer generation and citations

-   FR-033: Answers must be grounded in authorized retrieved evidence.
-   FR-034: The system must not invent policy values, conditions or
    deadlines.
-   FR-035: Answers must provide citations to source documents.
-   FR-036: Page/section references must be provided when available.
-   FR-037: The system must return a controlled no-answer response when
    evidence is insufficient.
-   FR-038: The system must surface unresolved conflicting sources.
-   FR-039: Effective dates and document versions must be considered.
-   FR-040: Citation references must be validated against retrieved
    evidence.
-   FR-041: Follow-up question handling is planned; ambiguous questions
    may require clarification.

### Conversations and feedback

-   FR-042: Users may create conversations.
-   FR-043: Conversations are private to their owner by default.
-   FR-044: Users may view their own conversation history.
-   FR-045: Each knowledge question must perform fresh permission-aware
    retrieval.
-   FR-046: Users may submit feedback on answers.

### Authorization and lifecycle

-   FR-047: Organization-wide documents are accessible only within the
    same organization and to authorized members.
-   FR-048: Department-specific documents require department membership
    or an explicit authorized delegate/grant.
-   FR-049: Restricted documents require an explicit user or role grant.
-   FR-050: Organization admin privileges do not automatically imply
    access to all restricted content.
-   FR-051: Cross-tenant retrieval must be prevented.
-   FR-052: Membership or grant revocation must affect subsequent
    retrieval.
-   FR-053: Archived documents must not be returned as active knowledge.
-   FR-054: Deleted documents must not be retrievable even if stale
    vectors remain temporarily.
-   FR-055: Cache or derived search results must not bypass current
    authorization.

### Guardrails and security

-   FR-056: Validate and constrain user input.
-   FR-057: Treat retrieved document text as untrusted data, not
    executable instructions.
-   FR-058: Enforce authorization before adding source text to model
    context.
-   FR-059: Support no-answer behavior.
-   FR-060: Validate citation IDs and source references.
-   FR-061: Use structured output where appropriate and validate it
    server-side.
-   FR-062: Defend against prompt injection in user questions and
    retrieved documents.
-   FR-063: Apply sensitive-data handling rules and avoid unnecessary
    exposure.
-   FR-064: Validate uploaded file type, integrity and configured
    limits.
-   FR-065: Apply configurable rate limits to sensitive/high-cost
    operations.
-   FR-066: Record security-relevant audit events.
-   FR-067: Do not use shared answer caching in the MVP.
-   FR-068: Handle LLM timeouts, rate limits and provider failures with
    controlled errors.
-   FR-069: Test guardrail and authorization behavior.
-   FR-070: Configurable sensitive-data detection is a later enhancement
    if justified.

## 3. Non-functional requirements

-   NFR-001 Security: tenant isolation and backend authorization are
    mandatory.
-   NFR-002 Reliability: ingestion failures must be visible and
    retryable.
-   NFR-003 Consistency: SQLite remains authoritative for content and
    permissions.
-   NFR-004 Retrieval: measure relevance and recall using a curated
    dataset.
-   NFR-005 Answer quality: measure groundedness, citation correctness
    and no-answer accuracy.
-   NFR-006 Performance: collect latency metrics before committing to
    numeric service-level targets.
-   NFR-007 Maintainability: modular monolith with clear module
    boundaries.
-   NFR-008 Observability: structured logs and request/job identifiers.
-   NFR-009 Privacy: avoid sending real confidential documents to an
    external LLM until provider data handling has been reviewed and
    approved.
-   NFR-010 Recovery: support retries, reconciliation and vector-index
    rebuild.
-   NFR-011 Auditability: record important permission, upload, archive
    and delete actions.
-   NFR-012 Migration: schema changes must be managed through
    migrations.
-   NFR-013 Resource control: bound file sizes, extraction work,
    concurrency and model calls.
-   NFR-014 Version awareness: preserve document versions and effective
    dates.

## 4. Business rules

-   BR-001: Tenant boundary is absolute.
-   BR-002: Authorization is checked before document text enters the LLM
    prompt.
-   BR-003: SQLite is the source of truth for users, permissions,
    document metadata and chunk text.
-   BR-004: ChromaDB is a rebuildable vector search index, not an
    authorization authority.
-   BR-005: Document lifecycle includes pending, processing, completed,
    failed, archived and deleted states.
-   BR-006: Preserve stable document identity and separate version
    identity.
-   BR-007: A new version becomes active only after successful
    processing and index verification.
-   BR-008: Date-dependent questions must use relevant effective
    versions; uncertainty must be stated if dates are ambiguous.
-   BR-009: Conflicts must be surfaced unless documented
    authority/effective-date metadata resolves them.
-   BR-010: Citations must reference actual source evidence used in the
    answer.
-   BR-011: Conversations are private by default.
-   BR-012: A previous assistant response is not trusted source evidence
    for a new knowledge question.

## 5. Acceptance test scenarios

-   AT-01: Authorized employee can retrieve an organization-wide policy.
-   AT-02: Employee without access cannot retrieve restricted HR
    content.
-   AT-03: Organization A cannot retrieve Organization B content.
-   AT-04: Unauthorized user cannot upload a document.
-   AT-05: Changing document visibility changes subsequent access.
-   AT-06: Revoking membership/grant prevents subsequent retrieval.
-   AT-07: Instructions embedded in a document are treated as untrusted
    content.
-   AT-08: User prompt cannot bypass backend authorization.
-   AT-09: Invalid citation reference is rejected.
-   AT-10: Unsupported policy deadline is not presented as verified.
-   AT-11: Insufficient evidence produces no-answer behavior.
-   AT-12: Conflicting active sources are surfaced.
-   AT-13: Archived document is excluded from active retrieval.
-   AT-14: Deleted document is not retrievable even if a stale vector
    remains.
-   AT-15: Any future cache is isolated by authorization scope and
    revalidated.
-   AT-16: Malformed or unavailable LLM response is handled safely.
-   AT-17: Partial ingestion retry does not create duplicate active
    chunks.
-   AT-18: Configured rate limits are enforced.

## 6. Baseline change control

This baseline is frozen for initial implementation. If a requirement
changes, document the reason and update this file and relevant design
documents. Do not silently reinterpret requirements.
