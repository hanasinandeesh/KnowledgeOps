# KnowledgeOps --- Logical Database Schema

**Status:** Design baseline. SQLAlchemy models and migrations are not
implemented yet.

## 1. Database principles

-   SQLite is the initial source of truth.
-   Use UUID-style identifiers for entities.
-   Store timestamps in UTC.
-   Enable SQLite foreign-key enforcement on every connection.
-   Include `organization_id` on tenant-owned records where appropriate.
-   Use migrations for schema changes.
-   Keep transactions short; never hold a database transaction open
    during external LLM/API calls.
-   ChromaDB is a derived search index, not the authoritative content or
    permission store.

## 2. Entities

### organizations

-   id (PK)
-   name
-   slug (unique)
-   status
-   created_at
-   updated_at

### users

-   id (PK)
-   email (unique according to account policy)
-   full_name
-   password_hash
-   status
-   created_at
-   updated_at

### organization_memberships

-   id (PK)
-   organization_id (FK)
-   user_id (FK)
-   role (employee, department_manager, organization_admin)
-   status
-   joined_at
-   unique organization_id + user_id

### departments

-   id (PK)
-   organization_id (FK)
-   name
-   created_at
-   unique organization_id + name

### user_departments

-   id (PK)
-   organization_id (FK)
-   user_id (FK)
-   department_id (FK)
-   role (member, delegate)
-   status

### documents

-   id (PK)
-   organization_id (FK)
-   title
-   description (nullable)
-   document_type
-   visibility (organization, department, restricted)
-   department_id (nullable FK)
-   uploaded_by (user FK)
-   status
-   created_at
-   updated_at

### document_versions

-   id (PK)
-   organization_id (FK)
-   document_id (FK)
-   version_number
-   storage_path
-   original_filename
-   mime_type
-   file_size_bytes
-   content_hash
-   effective_from (nullable)
-   effective_to (nullable)
-   processing_status
-   is_current
-   uploaded_at
-   unique document_id + version_number

A new version becomes current only after successful processing and index
verification.

### document_access_grants

-   id (PK)
-   organization_id (FK)
-   document_id (FK)
-   subject_type (user or role)
-   subject_id
-   permission (initially read)
-   granted_by (user FK)
-   created_at
-   revoked_at (nullable)

Application validation must ensure the subject belongs to the same
organization.

### ingestion_jobs

-   id (PK)
-   organization_id (FK)
-   document_version_id (FK)
-   status
-   attempts
-   max_attempts
-   locked_by (nullable)
-   locked_until (nullable)
-   last_error_code (nullable)
-   created_at
-   updated_at

Prevent duplicate active jobs for the same version.

### document_chunks

-   id (PK)
-   organization_id (FK)
-   document_id (FK)
-   document_version_id (FK)
-   department_id (nullable FK)
-   chunk_index
-   content
-   content_hash
-   page_number (nullable)
-   section_title (nullable)
-   token_count
-   created_at
-   unique document_version_id + chunk_index

### conversations

-   id (PK)
-   organization_id (FK)
-   user_id (owner FK)
-   title
-   status
-   created_at
-   updated_at

### messages

-   id (PK)
-   organization_id (FK)
-   conversation_id (FK)
-   role
-   content
-   status
-   model_name (nullable)
-   prompt_version (nullable)
-   created_at

### message_sources

-   id (PK)
-   message_id (FK)
-   chunk_id (FK)
-   document_version_id (FK)
-   citation_order
-   page_number (nullable)

### feedback

-   id (PK)
-   organization_id (FK)
-   message_id (FK)
-   user_id (FK)
-   rating
-   comment (nullable)
-   created_at

### audit_logs

-   id (PK)
-   organization_id (nullable FK for system-level events)
-   actor_user_id (nullable FK)
-   action
-   resource_type
-   resource_id
-   outcome
-   request_id
-   metadata (structured JSON text)
-   created_at

## 3. Search index

Use SQLite FTS5 as a derived full-text index over chunk content and
selected fields such as section title. It must be synchronized with
authoritative chunk records. It is not an authorization authority.

ChromaDB stores embedding vectors and metadata/references such as chunk
ID, organization ID, document ID, version ID, visibility and department
ID. Always revalidate candidates against SQLite before retrieving text.

## 4. Important indexes and constraints

Plan indexes for: - memberships by organization/user/status; -
department memberships by organization/user/department/status; -
documents by organization/status/visibility/department; - versions by
document/current status/effective dates; - grants by
organization/document/subject/revoked status; - jobs by status/lease; -
chunks by document version/chunk index; - conversations by
organization/user/updated time; - messages by conversation/created
time; - audit logs by organization/created time.

Use foreign keys and unique constraints to prevent invalid
relationships. Some cross-tenant consistency rules require service-level
validation or composite constraints.

## 5. Open implementation decisions

-   Exact SQLAlchemy types and UUID representation.
-   FTS5 synchronization strategy.
-   Grant subject modeling and role normalization.
-   Pagination and sorting conventions.
-   Password/session/token design.
-   Historical conversation behavior after access revocation.
-   Deletion and backup-retention policy.
-   SQLite concurrency limits and migration path to PostgreSQL.
