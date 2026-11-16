# KnowledgeOps --- Project Context Pack

This repository documentation pack is the working source of truth for
the KnowledgeOps MVP.

## How to use this pack

1.  Extract this folder into your Antigravity workspace.
2.  Open the `KnowledgeOps_Context_Pack` folder as the project
    workspace, or copy its contents into your existing `KnowledgeOps`
    repository.
3.  Read `AGENTS.md` first.
4.  Read `docs/product/PRODUCT_CONTEXT.md` to understand the product.
5.  Read `docs/engineering/PROJECT_DECISIONS_AND_OPEN_QUESTIONS.md`
    before changing architecture.
6.  Begin implementation only through a task in `tasks/active-task.md`.

## Document map

-   `AGENTS.md` --- instructions for Gemini and other coding agents.
-   `docs/product/PRODUCT_CONTEXT.md` --- product purpose, users, scope
    and examples.
-   `docs/requirements/REQUIREMENTS_BASELINE.md` --- functional and
    non-functional requirements.
-   `docs/architecture/HLD.md` --- high-level architecture.
-   `docs/architecture/LLD_INGESTION.md` --- document ingestion design.
-   `docs/architecture/LLD_RETRIEVAL.md` --- retrieval and RAG design.
-   `docs/architecture/LLD_CONVERSATIONS.md` --- conversation and
    LangGraph design.
-   `docs/architecture/SECURITY.md` --- security, privacy and
    failure-handling rules.
-   `docs/architecture/ADRs/ARCHITECTURE_DECISIONS.md` --- decisions and
    rationale.
-   `docs/database/SCHEMA.md` --- logical database schema.
-   `docs/api/API_CONTRACTS.md` --- initial API contracts.
-   `docs/engineering/DEVELOPMENT_WORKFLOW.md` --- engineering workflow
    and quality gates.
-   `docs/engineering/PROJECT_DECISIONS_AND_OPEN_QUESTIONS.md` ---
    confirmed, proposed and unresolved choices.
-   `docs/engineering/CURRENT_STATUS.md` --- honest project status.
-   `tasks/backlog.md` --- implementation roadmap.
-   `tasks/active-task.md` --- first implementation task.

## Status convention

-   **Confirmed**: explicitly selected or finalized in project
    discovery.
-   **Design baseline**: documented design, not yet implemented or
    verified.
-   **Proposed**: reasonable implementation suggestion that still needs
    review.
-   **Open**: requires a decision, benchmark or investigation.

Do not describe a design as implemented. Update `CURRENT_STATUS.md` only
after work has actually been completed and verified.
