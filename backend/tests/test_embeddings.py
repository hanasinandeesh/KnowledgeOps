import math

import pytest

from app.modules.indexing.embeddings import (
    DeterministicMockEmbeddingProvider,
    LocalSentenceTransformerEmbedding,
)
from app.modules.indexing.schemas import IndexingError


def test_deterministic_mock_embedding_dimensions() -> None:
    """Mock provider produces unit-normalized vectors of exact specified dimension."""
    provider = DeterministicMockEmbeddingProvider(dimension=384)
    assert provider.dimension == 384
    assert provider.model_id == "mock-model-384"

    vectors = provider.embed_documents(["First document chunk", "Second chunk"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384

    # Check vector is approximately unit-normalized (L2 norm ~ 1.0)
    norm = math.sqrt(sum(x * x for x in vectors[0]))
    assert pytest.approx(norm, rel=1e-4) == 1.0


def test_deterministic_mock_consistency() -> None:
    """Identical text produces identical embedding vectors."""
    provider = DeterministicMockEmbeddingProvider(dimension=384)
    vec1 = provider.embed_documents(["Acme travel policy reimbursement"])[0]
    vec2 = provider.embed_documents(["Acme travel policy reimbursement"])[0]
    assert vec1 == vec2


def test_local_sentence_transformer_empty_query_rejected() -> None:
    """Empty or whitespace query raises IndexingError."""
    provider = LocalSentenceTransformerEmbedding(model_id="BAAI/bge-small-en-v1.5")
    with pytest.raises(IndexingError) as exc_info:
        provider.embed_query("   ")
    assert exc_info.value.code == "EMPTY_QUERY_TEXT"


def test_local_sentence_transformer_lazy_loading() -> None:
    """Provider does not load PyTorch weights into memory until first embed call."""
    provider = LocalSentenceTransformerEmbedding(model_id="BAAI/bge-small-en-v1.5")
    assert provider._model is None
    assert provider.dimension == 384
