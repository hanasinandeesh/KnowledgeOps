# Engineering Decisions

| Area | Initial Proposal |
| :--- | :--- |
| **Chunking** | Structure-aware recursive splitting |
| **Chunk size** | 500 tokens |
| **Overlap** | 80 tokens |
| **Semantic retrieval** | Top 10 |
| **Keyword retrieval** | Top 10 |
| **Result combination** | RRF |
| **Initial final context** | Up to 5–8 chunks |
| **Reranking** | Deferred until benchmark |
| **Query embedding** | Same model as document embeddings |
| **LLM generation** | Groq |
| **No-answer** | Required |
| **Citation validation** | Required |
| **Permission checks** | Backend, before LLM context |

