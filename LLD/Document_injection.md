# Document Ingestion LLD

## 1. Objective

When an authorized HR manager uploads a leave policy, KnowledgeOps must:
- Validate the uploaded file.
- Store the original document.
- Extract its text.
- Split the text into meaningful chunks.
- Generate embeddings locally.
- Store vectors in ChromaDB.
- Store authoritative text and metadata in SQLite.
- Make the document available to authorized employees.

---

## 2. Detailed Ingestion Workflow

The API should not spend several minutes extracting and embedding a large document while the user waits for an HTTP response.

Instead, it accepts the document, creates an ingestion job, and returns a job identifier.

---

## 3. Internal Module Design

| Module | Responsibility |
| :--- | :--- |
| `documents` | Upload and document metadata |
| `file_validation` | Validate uploaded files |
| `document_storage` | Save original files |
| `text_extraction` | Extract PDF, DOCX and TXT content |
| `text_cleaning` | Normalize extracted content |
| `chunking` | Split content into chunks |
| `embeddings` | Generate local vectors |
| `vector_store` | Communicate with ChromaDB |
| `ingestion` | Coordinate the complete process |
| `ingestion_worker` | Execute pending ingestion jobs |

---

## 4. Chunking Strategy

This is an important design decision because the quality of retrieval depends heavily on how documents are divided.

### Example Scenario

Imagine this section of a company reimbursement policy:

> **Original document: Travel Reimbursement Policy**
> 
> **Section 1 — Eligibility**  
> Employees travelling for approved business purposes are eligible to claim expenses.
> 
> **Section 2 — Submission deadline**  
> Employees must submit reimbursement claims within 30 days of completing their business trip.
> 
> **Section 3 — Required documents**  
> Employees must provide receipts and supporting travel documents.

We should not blindly split the document at arbitrary character positions.

Instead, use **structure-aware chunking**:
1. Identify headings and sections.
2. Preserve section context.
3. Split long sections into smaller chunks.
4. Preserve page numbers and section names.
5. Apply controlled overlap when splitting within a section.

### Initial Chunking Configuration

| Parameter | Initial Value |
| :--- | :--- |
| **Chunk size** | 500 tokens |
| **Overlap** | 80 tokens |
| **Minimum chunk size** | 80 tokens |
| **Maximum chunk size** | 700 tokens |
| **Split preference** | Section → paragraph → sentence |
| **Token counting** | Selected embedding model tokenizer |

> *These are starting parameters, not proven optimal values.*

### Visual Example

**Document section:**
> *"Employees must submit reimbursement claims within 30 days of completing their business trip. Supporting receipts must be included."*

**Structure-aware chunking:**
- **Chunk 1:** *"Reimbursement claims must be submitted within 30 days of the business trip."*
- **Chunk 2:** *"Supporting receipts must be included with the reimbursement claim."*

*(Illustrative example only. Actual splitting depends on token size and document structure.)*

#### Why does this matter?
If an employee asks:
> *"How many days do I have to submit a claim?"*

The retrieval system should find the deadline chunk without needing the entire PDF.

---

## 5. Chunk Metadata Design

Each chunk needs metadata that allows us to trace it back to its source and enforce access control.

### Important Distinction:
- **SQLite** stores the chunk's actual text.
- **ChromaDB** stores the embedding and corresponding references/metadata.
- The metadata in ChromaDB is **not trusted** as the final authorization decision.

---

## 6. Ingestion Failure Handling

What happens if ChromaDB indexing fails after SQLite has stored the chunks? We must not mark the document as completed.

### Requirements:
- Idempotent job execution.
- Retry counters.
- Job leases or locks to avoid two workers processing the same job.
- Deterministic chunk IDs.
- A way to reconcile SQLite records with ChromaDB.
- A way to rebuild the vector index.

> [!IMPORTANT]
> For replacement or reprocessing, use a version-aware indexing strategy. Do not make a new version visible before it is fully indexed and validated.

