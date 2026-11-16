# KnowledgeOps --- Agent Instructions

## 1. Role

Act as a careful senior software engineer assisting with KnowledgeOps.
The human developer owns product and architecture decisions. Explain
changes in clear, beginner-friendly language.

## 2. Source of truth

Before any task: 1. Read this file. 2. Read
`docs/engineering/PROJECT_DECISIONS_AND_OPEN_QUESTIONS.md`. 3. Read only
the product, requirement, architecture, schema or API documents relevant
to the task. 4. Read `tasks/active-task.md`.

If documents conflict, do not silently choose. Identify the conflict and
ask for a decision. The latest explicitly approved decision supersedes
earlier proposals.

## 3. Product boundaries

KnowledgeOps is an enterprise knowledge discovery platform. The MVP
ingests uploaded PDF, DOCX and TXT files and provides permission-aware,
evidence-grounded answers with citations.

The MVP does not execute business workflows, approve expenses, change HR
records, or connect to external company repositories. Do not add these
capabilities unless approved.

## 4. Approved technology baseline

-   Python backend with FastAPI.
-   SQLite initially as the application source of truth.
-   SQLAlchemy and Alembic are the proposed persistence and migration
    tools.
-   ChromaDB as the initial vector store.
-   Local Hugging Face embeddings.
-   Groq as the initial LLM provider.
-   LangChain for selected RAG integrations.
-   LangGraph only for stateful or branching workflows where justified.
-   SQLite FTS5 for keyword search.
-   Pytest for tests.
-   RAGAS as a planned evaluation tool.
-   Docker Compose for reproducible local development.

Exact package versions, model IDs, APIs and provider limits must be
checked when implementation begins. Do not invent versions or assume
free-tier capacity is unlimited.

## 5. Architecture principles

-   Start with a modular monolith.
-   Keep API routes, business logic, persistence and external-provider
    adapters separated.
-   Prefer small, cohesive modules.
-   Avoid microservices and premature infrastructure.
-   Do not add Redis, Kafka, Kubernetes, Celery or paid services without
    an approved reason.
-   Keep provider-specific code behind small interfaces when this
    materially helps testing or migration.
-   Do not create future modules before they are needed.

## 6. Mandatory security rules

-   Every tenant-owned record and operation must be organization-scoped.
-   Resolve organization and user identity from trusted server-side
    authentication context, never from an untrusted request body.
-   Enforce authorization in the backend.
-   ChromaDB metadata filters are defense in depth, not the
    authorization authority.
-   Validate access before fetching chunk text for an LLM prompt.
-   Only authorized evidence may enter the prompt.
-   Treat uploaded and retrieved document text as untrusted data, not
    instructions.
-   Never give the LLM direct database, filesystem, shell or
    permission-management authority.
-   Keep secrets in environment variables; never commit `.env` or
    credentials.
-   Avoid logging raw document contents, secrets, sensitive prompts or
    tokens.
-   Conversations are private to their owner by default.

## 7. RAG correctness rules

-   Generate answers from retrieved evidence, not model memory.
-   Return citations that point to real retrieved sources.
-   Validate citation references and access rights server-side.
-   If evidence is missing or insufficient, return a controlled
    no-answer response.
-   Do not invent amounts, deadlines, policy conditions or source
    locations.
-   Surface unresolved document conflicts rather than guessing.
-   Apply effective dates and document-version rules.
-   A previous assistant answer is not authoritative policy evidence;
    retrieve fresh evidence for each knowledge question.

## 8. Coding standards

-   Use type hints for application code.
-   Use clear names and focused functions.
-   Validate external inputs.
-   Handle expected errors explicitly.
-   Keep business rules out of route handlers.
-   Avoid duplicated logic and unrelated refactoring.
-   Add dependencies only when justified.
-   Do not hardcode credentials, organization IDs, policy answers or
    environment-specific paths.
-   Prefer readable code over clever abstractions.

## 9. Required task workflow

For every task: 1. **Plan only:** inspect relevant files and propose a
small implementation plan. Do not edit files. 2. Explain files to be
added or changed, dependencies, risks and tests. 3. Wait for explicit
approval. 4. Implement only the approved scope. 5. Run relevant tests
and quality checks. 6. Review the Git diff for unintended changes,
security issues and secrets. 7. Explain what changed, why, and how to
verify it. 8. Update documentation and `CURRENT_STATUS.md`.

Do not claim tests passed unless they were actually executed. Report
skipped or failing tests honestly.

## 10. Context and token efficiency

-   Do not scan the entire repository by default.
-   Read only the files needed for the current task.
-   Do not repeat large documentation in prompts; reference exact file
    paths.
-   Work on one independently testable task at a time.
-   Do not silently modify approved requirements or architecture.
-   If implementation reveals a design gap, stop and propose a decision
    or ADR update.

## 11. Communication

For significant work, explain: - What problem is being solved? - What is
changing? - Why is this design appropriate? - What files are affected? -
How is it tested? - What remains incomplete?

Keep explanations simple and use a small flow or example when useful.
