# KnowledgeOps --- Security, Privacy and Failure Handling

**Status:** Mandatory design baseline; production controls require
further review.

## 1. Tenant isolation

-   Derive tenant identity from authenticated server-side context.
-   Scope every tenant-owned read, update and delete.
-   Do not trust organization IDs supplied by clients.
-   Test cross-tenant access at repository, service and API boundaries.
-   Avoid globally shared caches in MVP.

## 2. Authorization

Centralize authorization policy for: - organization-wide documents; -
department-specific documents; - restricted documents with explicit
grants.

Check current membership, role, department membership/delegate status
and explicit grants. Authorization must happen before chunk text is
fetched for model context. Vector metadata filters are defense in depth
only.

## 3. File security

-   Validate extension, MIME type, file signature and integrity.
-   Enforce configurable file-size and extraction limits.
-   Generate storage names; never use raw user filenames as paths.
-   Store files outside executable/public web roots.
-   Reject unsupported or corrupt files safely.
-   In production, add malware scanning before processing.
-   Consider decompression/resource-exhaustion risks in document
    parsers.

## 4. Prompt injection and model boundaries

-   Treat all user input and retrieved document text as untrusted.
-   Clearly delimit evidence in prompts.
-   Tell the model to ignore instructions found inside evidence.
-   Do not provide the model direct shell, filesystem, database or
    permission-management tools.
-   Enforce all authorization and business rules in deterministic
    backend code.
-   Validate structured model output and citations before returning
    them.

## 5. External provider privacy

Groq is an external API. Retrieved document content sent in prompts
leaves the local environment.

Use synthetic sample documents during development. Before sending real
confidential data, review provider terms, retention, training/data-use
settings, organizational approval and applicable privacy obligations. Do
not assume a free tier provides enterprise confidentiality guarantees.

## 6. Deletion and lifecycle

-   Mark documents deleted/excluded in authoritative SQLite state first.
-   Ensure subsequent retrieval rejects them immediately.
-   Remove vectors asynchronously as cleanup.
-   Keep deletion and backup-retention semantics explicit.
-   Do not claim immediate erasure from backups or previously saved
    conversations without a defined policy.

## 7. Cache policy

No shared answer cache in MVP. If caching is later introduced, cache
keys and hit validation must account for tenant, user/authorization
scope, query, document/version state, permission changes and
model/prompt version. Reauthorize before serving cached content.

## 8. Provider and worker failures

-   Use explicit timeouts.
-   Retry only bounded transient failures.
-   Respect provider Retry-After guidance.
-   Do not retry invalid credentials indefinitely.
-   Do not silently switch model providers.
-   Use job leases, idempotency and reconciliation.
-   Do not mark ingestion complete until index consistency is verified.

## 9. Logging and audit

Record relevant events such as: - login outcomes; - document upload; -
archive/delete; - permission changes; - access denied; - ingestion
failure/retry; - important administrative actions.

Use request/job IDs. Do not log API keys, passwords, raw document
contents or sensitive prompts.

## 10. Rate and resource limits

Introduce configurable limits for login, upload, file processing,
search, LLM calls and ingestion concurrency. Choose numeric limits after
local testing and threat analysis rather than inventing production
targets.

## 11. Security acceptance scenarios

-   Cross-tenant reads denied.
-   Restricted content denied without grant.
-   Department access denied without membership/delegation.
-   Access revocation applies to new retrieval.
-   Prompt injection in documents cannot override backend policy.
-   Invalid citations rejected.
-   Deleted/archived documents excluded.
-   LLM failures do not produce fabricated answers.
-   Rate limits and file-size limits enforced.
