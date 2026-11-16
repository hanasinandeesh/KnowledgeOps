# KnowledgeOps --- Low-Level Design: Conversations and AI Workflow

**Status:** Design baseline; implement only after core retrieval is
working.

## 1. Conversation behavior

-   Conversations are private to their owner by default.
-   A user may create, list and view their own conversations.
-   Messages and source references are persisted in SQLite.
-   A conversation does not grant access to documents.
-   Every knowledge question performs fresh permission-aware retrieval.
-   Prior assistant answers are not authoritative policy evidence.
-   No long-term employee profiling or memory is included in MVP.

## 2. Follow-up questions

For a follow-up such as "What about contractors?", the system may use
recent conversation context to form a standalone retrieval query.

If the reference is ambiguous, ask for clarification instead of
guessing.

The rewritten query must still go through fresh retrieval and
authorization checks.

## 3. Selective LangGraph workflow

Use LangGraph only if branching/state management materially improves the
conversation flow. Do not use a graph for every API endpoint or simple
operation.

Candidate nodes: - load_context - classify_query - rewrite_query -
validate_query - retrieve_evidence - check_evidence - generate_answer -
validate_answer - save_response

Possible outcomes: - clarification required; - insufficient
evidence/no-answer; - conflicting sources; - grounded answer; -
controlled provider error.

## 4. State fields

Candidate state: - organization_id - user_id - conversation_id -
original_question - conversation_history - standalone_question -
retrieved_candidates (references/metadata only until authorized) -
authorized_evidence - evidence_sufficient - clarification_required -
clarification_question - answer - citations - error

Keep retrieved candidates separate from authorized evidence. Never place
candidate text into the prompt before authorization.

## 5. Bounded execution

Provisional limits: - at most one query rewrite; - at most one
controlled transient generation retry; - at most one
citation-repair/regeneration attempt if justified.

Avoid unbounded graph loops. Keep retries configurable and observable.

## 6. Open policy question

Historical conversation behavior after access revocation needs a product
decision: whether previously displayed answers remain visible to the
conversation owner, are redacted, or are revalidated when history is
opened. Do not invent this policy. New retrieval requests must always
use current permissions.
