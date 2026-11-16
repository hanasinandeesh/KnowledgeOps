# Database Table Design

## A. Identity and Organization Tables

### `organizations`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `name` | VARCHAR(200) | Organization name |
| `slug` | VARCHAR(100) | Unique organization identifier |
| `status` | VARCHAR(20) | active / suspended |
| `created_at` | DATETIME | Creation time |
| `updated_at` | DATETIME | Last update |

---

### `users`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `email` | VARCHAR(255) | User email |
| `full_name` | VARCHAR(200) | Display name |
| `password_hash` | VARCHAR | Hashed password |
| `status` | VARCHAR(20) | active / disabled |
| `created_at` | DATETIME | Creation time |
| `updated_at` | DATETIME | Last update |

> **Note:** Use a unique normalized email strategy. Do not store plaintext passwords.

---

### `organization_memberships`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Organization |
| `user_id` | UUID | User |
| `role` | VARCHAR(30) | employee / manager / admin |
| `status` | VARCHAR(20) | active / revoked |
| `joined_at` | DATETIME | Membership start |

- **Unique constraint:** `(organization_id, user_id)`

---

### `departments`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `name` | VARCHAR(150) | Department name |
| `created_at` | DATETIME | Creation time |

- **Unique constraint:** `(organization_id, name)`

---

### `user_departments`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `user_id` | UUID | User |
| `department_id` | UUID | Department |
| `role` | VARCHAR(30) | member / delegate |
| `status` | VARCHAR(20) | active / inactive |

> **Note:** This supports users who belong to multiple departments.

---

## B. Documents and Permissions

### `documents`

A document represents a logical item, such as the Travel Reimbursement Policy, independent of its versions.

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `title` | VARCHAR(255) | Display title |
| `description` | TEXT | Optional description |
| `document_type` | VARCHAR(50) | policy / guide / technical |
| `visibility` | VARCHAR(30) | organization / department / restricted |
| `department_id` | UUID, nullable | Department scope |
| `uploaded_by` | UUID | User who uploaded |
| `status` | VARCHAR(20) | active / archived / deleted |
| `created_at` | DATETIME | Creation time |
| `updated_at` | DATETIME | Last update |

---

### `document_versions`

A document version represents a specific uploaded file and its processing state.

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `document_id` | UUID | Parent document |
| `version_number` | INTEGER | Version sequence |
| `storage_path` | TEXT | Internal storage reference |
| `original_filename` | VARCHAR(255) | Original filename |
| `mime_type` | VARCHAR(100) | Verified file type |
| `file_size_bytes` | BIGINT | File size |
| `content_hash` | VARCHAR(128) | Integrity and duplicate detection |
| `effective_from` | DATETIME, nullable | Policy effective start |
| `effective_to` | DATETIME, nullable | Policy effective end |
| `processing_status` | VARCHAR(20) | pending / processing / completed / failed |
| `is_current` | BOOLEAN | Current approved version |
| `uploaded_at` | DATETIME | Upload time |

- **Uniqueness constraint:** A uniqueness constraint should prevent duplicate version numbers within one document: `(document_id, version_number)`.
- **Important version rule:** A new version does not become current just because it was uploaded. It becomes current only after successful ingestion and an authorized activation decision.

---

### `document_access_grants`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `document_id` | UUID | Document |
| `subject_type` | VARCHAR(20) | user / role |
| `subject_id` | UUID or role identifier | Granted subject |
| `permission` | VARCHAR(20) | read |
| `granted_by` | UUID | Granting administrator |
| `created_at` | DATETIME | Grant time |
| `revoked_at` | DATETIME, nullable | Revocation time |

> **Note:** For MVP, use read grants only. Keep the schema extensible, but don't implement unnecessary permission types before they're needed.

---

## C. Ingestion and Retrieval

### `ingestion_jobs`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `document_version_id` | UUID | Version being processed |
| `status` | VARCHAR(20) | pending / processing / completed / failed |
| `attempts` | INTEGER | Number of attempts |
| `max_attempts` | INTEGER | Retry limit |
| `locked_by` | VARCHAR, nullable | Worker identity |
| `locked_until` | DATETIME, nullable | Lease expiry |
| `last_error_code` | VARCHAR, nullable | Safe failure code |
| `created_at` | DATETIME | Job creation |
| `updated_at` | DATETIME | Last update |

> **Note:** Use a unique active-job constraint or equivalent transactional logic to prevent duplicate processing requests for the same version.

---

### `document_chunks`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `document_id` | UUID | Parent document |
| `document_version_id` | UUID | Source version |
| `department_id` | UUID, nullable | Department metadata |
| `chunk_index` | INTEGER | Position in version |
| `content` | TEXT | Authoritative chunk text |
| `content_hash` | VARCHAR(128) | Stable content hash |
| `page_number` | INTEGER, nullable | Source page |
| `section_title` | VARCHAR(255), nullable | Source heading |
| `token_count` | INTEGER | Approximate/model token count |
| `created_at` | DATETIME | Creation time |

- **Unique constraint:** `(document_version_id, chunk_index)`
- **Vector store alignment:** Store the ChromaDB vector identifier deterministically from the chunk ID. ChromaDB metadata should include the identifiers and filters needed for retrieval, but SQLite remains authoritative.

---

## D. Conversation and Feedback

### `conversations`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `user_id` | UUID | Owner |
| `title` | VARCHAR(255) | Conversation title |
| `status` | VARCHAR(20) | active / archived |
| `created_at` | DATETIME | Creation |
| `updated_at` | DATETIME | Last update |

---

### `messages`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `conversation_id` | UUID | Parent conversation |
| `role` | VARCHAR(20) | user / assistant |
| `content` | TEXT | Message content |
| `status` | VARCHAR(20) | completed / failed |
| `model_name` | VARCHAR(100), nullable | Generation model |
| `prompt_version` | VARCHAR(50), nullable | Prompt revision |
| `created_at` | DATETIME | Creation time |

---

### `message_sources`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `message_id` | UUID | Assistant message |
| `chunk_id` | UUID | Source chunk |
| `document_version_id` | UUID | Source version |
| `citation_order` | INTEGER | Display order |
| `page_number` | INTEGER, nullable | Source location |

> **Note:** Store only sources actually used for the answer. Revalidate authorization when a user opens a source link.

---

### `feedback`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `message_id` | UUID | Assistant response |
| `user_id` | UUID | Feedback author |
| `rating` | VARCHAR(20) | helpful / not_helpful |
| `comment` | TEXT, nullable | Optional feedback |
| `created_at` | DATETIME | Creation |

---

## E. Audit

### `audit_logs`

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `id` | UUID | Primary key |
| `organization_id` | UUID | Tenant |
| `actor_user_id` | UUID, nullable | Acting user |
| `action` | VARCHAR(100) | Action type |
| `resource_type` | VARCHAR(50) | Document, user, conversation |
| `resource_id` | UUID, nullable | Affected record |
| `outcome` | VARCHAR(20) | success / denied / failure |
| `request_id` | VARCHAR(100), nullable | Request correlation |
| `metadata` | JSON, nullable | Safe structured details |
| `created_at` | DATETIME | Event time |

> **Security Note:** Avoid storing raw document text, passwords, API keys or sensitive prompts in audit metadata.

---

## 5. Important Database Constraints and Indexes

These are not optional performance decorations. They help preserve correctness.

| Table | Constraint or Index |
| :--- | :--- |
| `organizations` | Unique slug |
| `users` | Unique normalized email |
| `organization_memberships` | Unique organization + user |
| `departments` | Unique organization + name |
| `user_departments` | Unique organization + user + department |
| `documents` | Index organization + status |
| `document_versions` | Unique document + version number |
| `document_versions` | Index document + current status |
| `document_access_grants` | Index organization + document + subject |
| `ingestion_jobs` | Index status + locked_until |
| `document_chunks` | Unique version + chunk index |
| `document_chunks` | Index organization + document version |
| `conversations` | Index organization + user + updated time |
| `messages` | Index conversation + created time |
| `message_sources` | Unique message + chunk |
| `audit_logs` | Index organization + created time |

