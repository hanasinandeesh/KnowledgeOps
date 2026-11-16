# Observability and Evaluation Architecture

## Request Lifecycle Observability

We will record important stages of each RAG request:

| Stage | What to Measure |
| :--- | :--- |
| **Query validation** | Rejected requests |
| **Embedding** | Generation time and failures |
| **Semantic retrieval** | Search time and result count |
| **Keyword retrieval** | Search time and result count |
| **Permission validation** | Allowed and denied candidates |
| **Reranking** | Ranking time and relevance |
| **LLM generation** | Latency, tokens and failures |
| **Citation validation** | Valid and invalid citations |
| **Complete request** | End-to-end latency |

---

## Evaluation

For evaluation, build a small labelled dataset from synthetic company documents.

### Key Metrics to Measure:
- **Retrieval Precision@K** and **Recall@K**
- **MRR** or **nDCG** for ranking
- **Answer correctness and faithfulness**
- **Citation correctness**
- **No-answer behaviour**
- **Permission leakage tests**
- **Latency and model usage**

> [!NOTE]
> RAGAS can help evaluate RAG quality, but it does not replace deterministic security tests.

