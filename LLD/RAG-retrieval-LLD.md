# RAG Retrieval LLD

## 1. Objective

An employee asks:
> *"How many days do I have to submit my travel reimbursement claim?"*

KnowledgeOps must:
1. Authenticate the employee.
2. Identify their organization and permissions.
3. Search authorized documents.
4. Combine semantic and keyword search.
5. Verify document permissions.
6. Retrieve authoritative chunk text.
7. Generate an evidence-based answer through Groq.
8. Verify citations.
9. Save the conversation.

---

## 2. Semantic Search Using ChromaDB

The Hugging Face embedding model converts the employee's question into a vector.

**Conceptually:**  
ChromaDB compares this vector against the document chunk vectors and returns similar candidates.

### Example Candidate Results:

| Chunk | Document | Similarity / Rank |
| :--- | :--- | :--- |
| `C001` | Travel reimbursement policy | 1 |
| `C005` | Employee travel handbook | 2 |
| `C012` | Finance guidelines | 3 |

> *These are candidates, not yet authorized final results.*

---

## 3. Keyword Search Using SQLite FTS5

Semantic search understands meaning. Keyword search helps find exact terminology.

For example, a user may ask:
> *"What is the LTA limit?"*

The document might contain the exact term **LTA**.

We will use SQLite FTS5 to search the authoritative chunk text.

```sql
SELECT
    chunk_id,
    document_id,
    rank
FROM chunks_fts
WHERE chunks_fts MATCH :query
ORDER BY rank
LIMIT 10;
```

> *This is illustrative SQL; we will finalize the FTS table and query implementation in Stage 5.*

---

## 4. Hybrid Retrieval

We combine the results from both retrieval systems.

### Hybrid Search Example

* **Semantic Search:** `C001`, `C005`, `C012`
* **Keyword Search:** `C001`, `C009`, `C012`

#### Merge and Deduplicate

**Combined candidates:**  
`C001` · `C005` · `C012` · `C009`

We can use **Reciprocal Rank Fusion (RRF)** to combine the rankings without needing to compare raw semantic similarity scores with FTS5 scores.

---

## 5. Permission Validation

This is the most important security stage.

Imagine ChromaDB returns four candidate chunks:

| Candidate | Visibility | Employee Access |
| :--- | :--- | :--- |
| `C001` | Organization-wide | Allowed |
| `C005` | Engineering | Allowed |
| `C012` | Restricted HR | Denied |
| `C009` | Another organization | Denied |

**Result:** Only `C001` and `C005` should continue.

### Validation Checklist:
- Organization ID.
- Document lifecycle status.
- Document version status and effective dates.
- Organization-wide, department or restricted visibility.
- Department membership.
- Explicit user or role grants.
- Any relevant access revocation.

> [!CAUTION]
> **Never send unauthorized candidate text to Groq.** Ideally, fetch the chunk content from SQLite only after checking the authoritative document and permission records.

---

## 6. Reranking

After permission validation, we have a set of relevant candidates.

Reranking attempts to improve their order by judging how well each candidate answers the actual question.

### For the MVP:
- Use RRF to combine semantic and keyword results.
- Apply deterministic filters for version and source eligibility.
- Avoid adding a separate reranking model immediately.
- Add a local cross-encoder reranker later if evaluation demonstrates a meaningful improvement.

This keeps initial infrastructure and memory requirements low.

