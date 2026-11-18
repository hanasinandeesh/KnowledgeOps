import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.indexing.schemas import IndexingError

logger = logging.getLogger("knowledgeops.indexing.vector_store")


class BaseVectorStore(ABC):
    """Abstract interface for vector index operations."""

    @abstractmethod
    def upsert_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> int:
        """Upsert vectors, metadata, and texts into the vector index."""
        pass

    @abstractmethod
    def delete_by_version(self, document_version_id: str) -> int:
        """Purge all indexed vectors belonging to a specific document version."""
        pass

    @abstractmethod
    def count_by_version(self, document_version_id: str) -> int:
        """Return the count of indexed vectors for a specific version."""
        pass

    @abstractmethod
    def get_collection_count(self) -> int:
        """Return total number of vectors in the collection."""
        pass


class ChromaVectorStore(BaseVectorStore):
    """Persistent local ChromaDB vector store using cosine distance space."""

    def __init__(
        self,
        persist_path: Path | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.persist_path = persist_path or settings.CHROMA_PERSISTENCE_PATH
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self._client: Any = None
        self._collection: Any = None

    def _ensure_collection(self) -> Any:
        """Lazily initialize persistent client and collection."""
        if self._collection is None:
            try:
                import chromadb

                self.persist_path.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(path=str(self.persist_path))
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info(
                    f"Connected to ChromaDB at '{self.persist_path}' "
                    f"(collection: '{self.collection_name}')."
                )
            except Exception as e:
                logger.exception(f"Failed to initialize ChromaDB: {e}")
                err_msg = (
                    f"Failed to initialize ChromaDB collection "
                    f"'{self.collection_name}': {e}"
                )
                raise IndexingError(
                    err_msg,
                    code="VECTOR_STORE_INIT_ERROR",
                ) from e
        return self._collection

    def upsert_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> int:
        """Upsert vectors in batches to ChromaDB. Returns total number upserted."""
        if not chunk_ids:
            return 0

        if not (len(chunk_ids) == len(embeddings) == len(metadatas) == len(documents)):
            raise IndexingError(
                f"Mismatched batch lengths: chunk_ids={len(chunk_ids)}, "
                f"embeddings={len(embeddings)}, metadatas={len(metadatas)}, "
                f"documents={len(documents)}",
                code="VECTOR_BATCH_LENGTH_MISMATCH",
            )

        collection = self._ensure_collection()
        batch_size = 200

        try:
            total_upserted = 0
            for i in range(0, len(chunk_ids), batch_size):
                end = i + batch_size
                b_ids = chunk_ids[i:end]
                b_emb = embeddings[i:end]
                b_meta = metadatas[i:end]
                b_docs = documents[i:end]

                collection.upsert(
                    ids=b_ids,
                    embeddings=b_emb,
                    metadatas=b_meta,
                    documents=b_docs,
                )
                total_upserted += len(b_ids)

            logger.info(
                f"Successfully upserted {total_upserted} chunks into Chroma collection "
                f"'{self.collection_name}'."
            )
            return total_upserted
        except Exception as e:
            logger.exception(f"Failed to upsert chunks into ChromaDB: {e}")
            raise IndexingError(
                f"Failed to upsert chunks into ChromaDB: {e}",
                code="VECTOR_UPSERT_ERROR",
            ) from e

    def delete_by_version(self, document_version_id: str) -> int:
        """Delete all vectors matching document_version_id."""
        collection = self._ensure_collection()
        try:
            # Query existing IDs for this version to know count
            existing = collection.get(
                where={"document_version_id": document_version_id}
            )
            count = len(existing.get("ids", []))
            if count > 0:
                collection.delete(where={"document_version_id": document_version_id})
                logger.info(
                    f"Deleted {count} vectors for version '{document_version_id}'."
                )
            return count
        except Exception as e:
            logger.exception(
                f"Failed to delete vectors for version '{document_version_id}': {e}"
            )
            raise IndexingError(
                f"Failed to delete vectors for version '{document_version_id}': {e}",
                code="VECTOR_DELETE_ERROR",
            ) from e

    def count_by_version(self, document_version_id: str) -> int:
        """Count vectors indexed for document_version_id."""
        collection = self._ensure_collection()
        try:
            existing = collection.get(
                where={"document_version_id": document_version_id}
            )
            return len(existing.get("ids", []))
        except Exception as e:
            logger.exception(
                f"Failed to count vectors for version '{document_version_id}': {e}"
            )
            raise IndexingError(
                f"Failed to count vectors for version '{document_version_id}': {e}",
                code="VECTOR_COUNT_ERROR",
            ) from e

    def get_collection_count(self) -> int:
        """Return total vector count in collection."""
        collection = self._ensure_collection()
        return collection.count()
