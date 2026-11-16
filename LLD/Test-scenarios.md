# Test Scenarios

## Ingestion Tests

| Test | Expected Behaviour |
| :--- | :--- |
| Upload valid PDF | Accepted |
| Upload DOCX | Accepted |
| Upload TXT | Accepted |
| Upload unsupported format | Rejected |
| Upload corrupted file | Rejected |
| Extract text successfully | Text persisted |
| Chunk document | Correct chunk references |
| Embedding service fails | Job retryable |
| Chroma indexing fails | Not marked completed |
| Same job retries | No duplicate active chunks |
| New document version | Version history preserved |

---

## Retrieval Tests

| Test | Expected Behaviour |
| :--- | :--- |
| Ask question about leave policy | Relevant chunks retrieved |
| Exact keyword query | FTS5 finds matching content |
| Semantic paraphrase | Relevant meaning retrieved |
| Both search systems return same chunk | Deduplicated |
| Cross-tenant result appears | Rejected |
| Restricted HR document | Rejected |
| Archived document | Excluded |
| Insufficient evidence | No-answer |
| Invalid citation | Rejected |
| Groq API fails | Controlled error |
| Permission revoked | Subsequent retrieval denied |

