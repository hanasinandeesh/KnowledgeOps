import logging
from typing import Any

from app.modules.indexing.chunker import TextChunker
from app.modules.indexing.embeddings import (
    BaseEmbeddingProvider,
    LocalSentenceTransformerEmbedding,
)
from app.modules.indexing.schemas import (
    ChunkMetadata,
    IndexingError,
    IndexingResult,
    TextChunk,
)
from app.modules.indexing.vector_store import BaseVectorStore, ChromaVectorStore

logger = logging.getLogger("knowledgeops.indexing.service")


class IndexingService:
    """Orchestrates document chunking, embeddings, and ChromaDB vector indexing."""

    def __init__(
        self,
        chunker: TextChunker | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
        vector_store: BaseVectorStore | None = None,
    ) -> None:
        self.chunker = chunker or TextChunker()
        self.embedding_provider = (
            embedding_provider or LocalSentenceTransformerEmbedding()
        )
        self.vector_store = vector_store or ChromaVectorStore()

    def process_and_index_pages(
        self,
        pages: list[Any],
        organization_id: str,
        document_id: str,
        document_version_id: str,
        visibility: str,
        department_id: str | None = None,
    ) -> tuple[list[TextChunk], IndexingResult]:
        """Transform extracted pages into chunks, embed them, and index in ChromaDB.

        Returns the generated TextChunks and IndexingResult.
        Raises IndexingError if any step fails.
        """
        # Step 1: Chunk pages into structured units
        chunks = self.chunker.chunk_pages(pages)
        if not chunks:
            raise IndexingError(
                "Document produced 0 text chunks during chunking",
                code="EMPTY_CHUNKS_ERROR",
            )

        logger.info(
            f"Generated {len(chunks)} chunks for version '{document_version_id}'"
        )

        # Step 2: Generate local vector embeddings
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedding_provider.embed_documents(chunk_texts)

        # Step 3: Build deterministic chunk IDs and ChromaDB scalar metadata
        chunk_ids: list[str] = []
        metadatas: list[dict[str, Any]] = []

        safe_dept = department_id or ""
        for chunk in chunks:
            c_id = f"{document_version_id}_c{chunk.chunk_index}"
            chunk_ids.append(c_id)

            meta = ChunkMetadata(
                chunk_id=c_id,
                organization_id=organization_id,
                document_id=document_id,
                document_version_id=document_version_id,
                department_id=safe_dept,
                visibility=visibility,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number if chunk.page_number is not None else -1,
                section_title=chunk.section_title or "",
                token_count=chunk.token_count,
                content_hash=chunk.content_hash,
            )
            metadatas.append(meta.to_dict())

        # Step 4: Upsert into ChromaDB
        total_upserted = self.vector_store.upsert_chunks(
            chunk_ids=chunk_ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=chunk_texts,
        )

        # Step 5: Verify Chroma count
        indexed_count = self.vector_store.count_by_version(document_version_id)
        if indexed_count != len(chunks):
            # Clean up on verification mismatch
            self.vector_store.delete_by_version(document_version_id)
            raise IndexingError(
                f"Vector indexing count mismatch: expected {len(chunks)} chunks, "
                f"found {indexed_count} in ChromaDB",
                code="INDEXING_COUNT_MISMATCH",
            )

        result = IndexingResult(
            document_version_id=document_version_id,
            chunk_count=len(chunks),
            indexed_vector_count=total_upserted,
            model_id=self.embedding_provider.model_id,
            success=True,
        )

        logger.info(
            f"Successfully indexed version '{document_version_id}': "
            f"{len(chunks)} chunks in ChromaDB."
        )
        return chunks, result

    def purge_version_vectors(self, document_version_id: str) -> int:
        """Purge vectors for a superseded or failed version."""
        return self.vector_store.delete_by_version(document_version_id)
