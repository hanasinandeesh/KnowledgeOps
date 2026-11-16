# KnowledgeOps --- Development Workflow

## 1. Developer environment

Current user-selected setup: - IDE: Google Antigravity. - Primary coding
assistant: Gemini. - OS/terminal working assumption: Windows with
PowerShell; confirm actual environment before commands that depend on
it.

Working Python version: 3.12 candidate. Verify installed package
compatibility before pinning dependencies.

## 2. Workspace rules

-   Open the KnowledgeOps repository root as the Antigravity workspace.
-   Keep `AGENTS.md` at the repository root.
-   Keep product and technical context in version-controlled Markdown
    files.
-   Do not rely on an AI assistant remembering previous chat context.
-   Review file edits and terminal commands before approval.

## 3. Task loop

### A. Plan only

Ask Gemini to read `AGENTS.md`, the relevant design docs and
`tasks/active-task.md`. Request a plan only. No file changes.

### B. Review plan

Check scope, files, dependencies, security, tests and assumptions. Ask
questions before approval.

### C. Implement

Approve one small task. Avoid unrelated refactoring or broad code
generation.

### D. Verify

Run relevant tests, lint and formatting checks. Inspect failures rather
than hiding them.

### E. Review

Inspect `git diff`, check secrets, authorization boundaries, unintended
files and consistency with docs.

### F. Document

Update task status and `CURRENT_STATUS.md`. Update architecture
docs/ADRs if a decision changed.

## 4. Git workflow

Keep Git simple: - `main` is the stable branch. - Use short-lived
feature branches for meaningful work. - Commit in small units.

Suggested commit prefixes: - `feat:` - `fix:` - `test:` - `docs:` -
`refactor:` - `chore:`

Do not force complex Git Flow for a solo MVP.

## 5. Initial quality tools

-   Ruff for linting/formatting.
-   Pytest for automated tests.
-   HTTPX test client for API tests where appropriate.
-   Type checking may be added when the codebase stabilizes.
-   Avoid adding a large quality-tool stack before there is a need.

## 6. Environment and secrets

-   Keep credentials in local `.env`.
-   Commit `.env.example` with placeholder names only.
-   Add `.env`, virtual environments, databases, uploaded files,
    vector-store data, caches and build artifacts to `.gitignore`.
-   Never paste real API keys into prompts or source code.

## 7. Definition of Done

A task is complete only when: - behavior and acceptance criteria are
clear; - implementation matches approved design; - validation and error
paths are handled; - relevant tests are written and executed; - relevant
lint/format checks are executed; - Git diff is reviewed; - no secrets
are committed; - docs and status are updated.

A generated implementation is not automatically a completed feature.
