import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.indexing.schemas import IndexingError

logger = logging.getLogger("knowledgeops.indexing.embeddings")


class BaseEmbeddingProvider(ABC):
    """Abstract interface for generating vector embeddings."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of document chunk texts."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single search query text."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality of this embedding model."""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return the identifier of this embedding model."""
        pass


class LocalSentenceTransformerEmbedding(BaseEmbeddingProvider):
    """Local Hugging Face sentence transformer embedding provider running on CPU."""

    def __init__(
        self,
        model_id: str | None = None,
        cache_dir: Path | None = None,
        batch_size: int = 16,
    ) -> None:
        self._model_id = model_id or settings.EMBEDDING_MODEL_ID
        self._cache_dir = cache_dir or settings.EMBEDDING_CACHE_DIR
        self._batch_size = batch_size
        self._model: Any = None
        # Standard 384 dimensions for BAAI/bge-small-en-v1.5 and all-MiniLM-L6-v2
        self._dimension = 384

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def _ensure_model_loaded(self) -> Any:
        """Lazily load SentenceTransformer model onto CPU."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._cache_dir.mkdir(parents=True, exist_ok=True)
                logger.info(
                    f"Loading local embedding model '{self._model_id}' on CPU "
                    f"(cache: {self._cache_dir})..."
                )
                self._model = SentenceTransformer(
                    self._model_id,
                    cache_folder=str(self._cache_dir),
                    device="cpu",
                )
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(
                    f"Loaded '{self._model_id}' successfully (dim={self._dimension})."
                )
            except Exception as e:
                logger.exception(
                    f"Failed to load embedding model '{self._model_id}': {e}"
                )
                raise IndexingError(
                    f"Failed to load embedding model '{self._model_id}': {e}",
                    code="EMBEDDING_MODEL_LOAD_ERROR",
                ) from e
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate normalized vector embeddings for chunk texts."""
        if not texts:
            return []

        model = self._ensure_model_loaded()
        try:
            embeddings = model.encode(
                texts,
                batch_size=self._batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            return embeddings.tolist()
        except Exception as e:
            logger.exception(f"Error encoding document chunks: {e}")
            raise IndexingError(
                f"Embedding generation failed: {e}",
                code="EMBEDDING_GENERATION_ERROR",
            ) from e

    def embed_query(self, text: str) -> list[float]:
        """Generate normalized vector embedding for a single query."""
        clean_text = text.strip()
        if not clean_text:
            raise IndexingError("Query text cannot be empty", code="EMPTY_QUERY_TEXT")

        # For BGE models, query instruction prefix improves retrieval performance
        query_input = clean_text
        if "bge" in self._model_id.lower() and not clean_text.startswith(
            "Represent this sentence"
        ):
            query_input = (
                f"Represent this sentence for searching relevant passages: {clean_text}"
            )

        embeddings = self.embed_documents([query_input])
        return embeddings[0]


class DeterministicMockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic mock embedding provider for fast unit tests without Torch."""

    def __init__(self, dimension: int = 384, model_id: str = "mock-model-384") -> None:
        self._dimension = dimension
        self._model_id = model_id

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_vector(self, text: str) -> list[float]:
        import hashlib
        import math

        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [(b / 255.0) - 0.5 for b in h]
        # Repeat/truncate to reach self._dimension
        repeated = (vec * ((self._dimension // len(vec)) + 1))[: self._dimension]
        # Normalize
        norm = math.sqrt(sum(x * x for x in repeated)) or 1.0
        return [x / norm for x in repeated]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._generate_vector(text)
