# Provider Abstraction Pattern & Migration Design

## Provider Abstraction Pattern

The **KnowledgeOps Application** calls stable interfaces:

* **LLM Interface:**
  * **Current:** Groq (now)
  * **Future:** Other provider (later)
* **Vector Interface:**
  * **Current:** Chroma (now)
  * **Future:** Qdrant (later)
* **Database Interface:**
  * **Current:** SQLite (now)
  * **Future:** PostgreSQL (later)

---

## Example Configuration

```env
LLM_PROVIDER=groq
EMBEDDING_PROVIDER=huggingface
VECTOR_STORE=chroma
DATABASE_URL=sqlite:///./data/sqlite/knowledgeops.db
```

> **Note:** These values should be validated at application startup.

---

## Migration Roadmap

When we migrate:

| Component | Current | Future |
| :--- | :--- | :--- |
| **LLM** | Groq free API | Paid or alternative LLM |
| **Embeddings** | Local Hugging Face | Alternative embedding provider |
| **Vector Store** | ChromaDB | Managed or self-hosted vector database |
| **Relational Database** | SQLite | PostgreSQL |
| **File Storage** | Local file storage | Object storage |
| **Worker / Queue** | SQLite-backed worker | Celery + Redis |

---

## Controlled Migration Guidelines

> [!IMPORTANT]
> - **Replacing an embedding provider** means rebuilding the vector index with the new embedding model.
> - **Replacing the vector database** means migrating and validating the index.
> 
> These are controlled migrations, not magic configuration switches.

