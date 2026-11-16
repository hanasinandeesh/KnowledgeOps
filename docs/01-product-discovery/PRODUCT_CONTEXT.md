# KnowledgeOps --- Product Context

## 1. Product identity

**Name:** KnowledgeOps  
**Category:** Enterprise Knowledge Intelligence Platform (Single-Organization Deployment)  
**Deployment Model:** Dedicated, single-organization enterprise system (not a public multi-tenant SaaS)

**Vision:** Enable employees within the organization to discover, understand and verify company knowledge through a secure, centralized, internal intelligence platform.

**Positioning statement:** KnowledgeOps is a dedicated enterprise knowledge discovery platform for a single organization. It helps employees find, understand and verify organizational information from company documents using departmental permission-aware retrieval and evidence-grounded AI answers with verifiable citations.

## 2. Problem statement

Within an enterprise, organizational knowledge is frequently fragmented across disconnected documents, departmental drives, and team silos. Employees spend valuable hours searching for policies, asking colleagues, or submitting routine inquiries to HR, Legal, or Finance. They frequently encounter outdated versions or misunderstand policy conditions and exceptions.

This fragmentation creates:
- Repeated routine inquiries that interrupt team productivity.
- Delays in decision-making and operational bottlenecks.
- Inconsistent interpretation of corporate policies and guidelines.

KnowledgeOps resolves this friction by serving as the unified, authoritative internal knowledge engine where authorized employees can ask natural-language questions and receive grounded answers backed by real document citations.

## 3. Target organization scope

- **Deployment Model:** Single-tenant / dedicated enterprise deployment for one organization.
- **Enterprise Scale:** Designed for mid-sized to large enterprises (typically 100 to 1,000+ employees).
- **Security Boundary:** The enterprise organization is the root boundary. The platform does not host multiple competing external tenants on a shared database.
- **Internal Segmentation:** Within the enterprise, information is segregated by departments (e.g., Engineering, Sales, HR, Legal, Finance) and confidentiality levels.

## 4. Users and roles

### Employee
- Search and query internal company documents they are authorized to access.
- Ask questions in natural language and receive answers grounded strictly in retrieved evidence.
- Inspect source citations with page numbers and document titles.
- Create and manage private question-and-answer conversations.
- Submit answer feedback (thumbs up/down and comments).

### Department Manager
- Manage and upload documentation specific to their department (e.g., Engineering runbooks, Sales playbooks).
- Inspect document ingestion and indexing statuses for their department.
- Departmental authority does not automatically grant access to confidential documents in other departments or restricted executive files.

### Organization Admin (System Administrator)
- Manage the enterprise workspace, internal user accounts, departmental structures, and global configuration.
- Upload and manage company-wide policies (e.g., Employee Handbook, Corporate Travel & Expense Policy).
- System administration permissions do not automatically grant content access to restricted or confidential documents.

## 5. Core example

An employee asks: *"What is the reimbursement limit for a client dinner, and what receipts are required?"*

KnowledgeOps will:
1. Identify the authenticated employee, their department memberships, and role.
2. Search relevant company policies.
3. Enforce document visibility and access permissions.
4. Retrieve authorized source chunks.
5. Verify whether evidence is sufficient and current.
6. Generate an answer grounded strictly in that authorized evidence.
7. Return the answer with exact citations pointing to the source document, version, and page number.

If the employee belongs to Sales, they may see general company policies plus Sales-specific travel guides, while an employee without access cannot retrieve confidential executive travel files.

## 6. MVP scope

### Included
- Single-organization enterprise backend and database foundation.
- Internal employee authentication (JWT access tokens with bcrypt password hashing).
- Internal departmental membership and role modeling.
- PDF, DOCX, and TXT document uploads.
- Three-tier internal visibility model: Organization-wide, Department-specific, and Restricted.
- Document versioning, metadata tracking, and audit history.
- Asynchronous document ingestion and background job queue.
- Text extraction, normalization, and source-preserving chunking.
- Local embeddings and ChromaDB vector search index.
- SQLite FTS5 keyword search and hybrid search with Reciprocal Rank Fusion (RRF).
- Strict backend authorization enforcement before document text enters the LLM prompt.
- Evidence-grounded generation using Groq LLM with citations and controlled no-answer behavior.
- Private employee conversations and feedback collection.
- Standardized security guardrails and automated testing.

### Excluded from MVP
- Multi-tenant SaaS billing, tenant switching, or public multi-client hosting.
- Executing business transactions (e.g., submitting expense reimbursements or modifying HR records).
- Automatic live sync with external third-party repositories (Google Drive, SharePoint).
- Microservices architecture or premature distributed infrastructure (no Redis, Kafka, or Kubernetes required initially).
- Complex multi-agent autonomous orchestration.
- Long-term personal profiling or surveillance of individual employees.

## 7. Document visibility and access tiers

KnowledgeOps organizes enterprise knowledge into three internal visibility tiers:

1. **Organization-wide:**
   - Universal company policies and procedures available to all active employees across the entire organization (e.g., Code of Conduct, Benefits Guide, Holiday Schedule).
   - Uploading is restricted to Organization Admins and authorized managers.

2. **Department-specific:**
   - Operational documentation scoped strictly to members and delegates of a specific internal department (e.g., Engineering Architecture Guidelines, Sales Onboarding, HR Internal Protocols).
   - Requires active department membership or an explicit delegate grant.

3. **Restricted (Confidential):**
   - Sensitive or confidential materials accessible exclusively to explicitly designated individuals or roles (e.g., Board Minutes, M&A Strategy, Executive Compensation).
   - Organization Admins do not automatically receive access to restricted content without an explicit grant.

All authorization checks are enforced deterministically in backend code before chunk text is loaded or injected into an LLM prompt.

## 8. Product principles

- **Trust over fluency:** An answer must be verifiable with citations; an ungrounded or hallucinated answer is treated as a defect.
- **Permission enforcement before generation:** The LLM prompt receives only evidence the requesting employee is authorized to read.
- **Document freshness and version awareness:** Active document versions take precedence; outdated or superseded policies must not be presented as active truth.
- **Explicit uncertainty:** If authoritative evidence is missing, contradictory, or insufficient, the system returns a controlled no-answer response rather than guessing.
- **Private by default:** Employee queries and conversation histories are private to their creator.
- **Simplicity and modularity:** Start with a cohesive modular monolith designed for clean enterprise operations.

## 9. Product success metrics

The success of the single-organization platform will be measured by:
- **Search relevance and recall:** Employees quickly locate the exact policies and standards they need.
- **Citation accuracy:** Citations point accurately to real source documents and verified page/section numbers.
- **Zero unauthorized exposure:** Employees never receive answers or citations derived from documents outside their authorized department or visibility level.
- **Reliable ingestion:** Document updates and new uploads are indexed and made available without corrupting active versions.
- **Controlled failure handling:** Insufficient evidence triggers helpful, transparent uncertainty rather than fabricated policy amounts or deadlines.
