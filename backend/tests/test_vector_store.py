from pathlib import Path

import pytest

from app.modules.indexing.schemas import IndexingError
from app.modules.indexing.vector_store import ChromaVectorStore


@pytest.fixture
def chroma_store(tmp_path: Path) -> ChromaVectorStore:
    """Provides a ChromaVectorStore isolated to a temporary directory."""
    persist_dir = tmp_path / "chroma_test_db"
    return ChromaVectorStore(
        persist_path=persist_dir,
        collection_name="test_collection",
    )


def test_chroma_upsert_and_count(chroma_store: ChromaVectorStore) -> None:
    """Vectors and metadata are successfully upserted and counted."""
    chunk_ids = ["v1_c0", "v1_c1"]
    embeddings = [[0.1] * 384, [0.2] * 384]
    metadatas = [
        {"document_version_id": "v1", "chunk_index": 0, "department_id": ""},
        {"document_version_id": "v1", "chunk_index": 1, "department_id": ""},
    ]
    docs = ["Content of chunk 0", "Content of chunk 1"]

    upserted = chroma_store.upsert_chunks(chunk_ids, embeddings, metadatas, docs)
    assert upserted == 2
    assert chroma_store.count_by_version("v1") == 2
    assert chroma_store.get_collection_count() == 2


def test_chroma_idempotent_upsert(chroma_store: ChromaVectorStore) -> None:
    """Re-upserting the same chunk IDs replaces existing records without duplicates."""
    chunk_ids = ["v1_c0"]
    embeddings = [[0.1] * 384]
    metadatas = [{"document_version_id": "v1", "chunk_index": 0, "department_id": ""}]
    docs = ["Initial text"]

    chroma_store.upsert_chunks(chunk_ids, embeddings, metadatas, docs)
    assert chroma_store.count_by_version("v1") == 1

    # Upsert updated content with same ID
    docs_updated = ["Updated text"]
    chroma_store.upsert_chunks(chunk_ids, embeddings, metadatas, docs_updated)
    assert chroma_store.count_by_version("v1") == 1
    assert chroma_store.get_collection_count() == 1


def test_chroma_delete_by_version(chroma_store: ChromaVectorStore) -> None:
    """Deleting by version ID removes all and only vectors for that version."""
    chunk_ids = ["v1_c0", "v2_c0"]
    embeddings = [[0.1] * 384, [0.2] * 384]
    metadatas = [
        {"document_version_id": "v1", "chunk_index": 0, "department_id": ""},
        {"document_version_id": "v2", "chunk_index": 0, "department_id": ""},
    ]
    docs = ["Version 1", "Version 2"]

    chroma_store.upsert_chunks(chunk_ids, embeddings, metadatas, docs)
    assert chroma_store.count_by_version("v1") == 1
    assert chroma_store.count_by_version("v2") == 1
    assert chroma_store.get_collection_count() == 2

    # Purge version 1
    deleted_count = chroma_store.delete_by_version("v1")
    assert deleted_count == 1
    assert chroma_store.count_by_version("v1") == 0
    assert chroma_store.count_by_version("v2") == 1
    assert chroma_store.get_collection_count() == 1


def test_chroma_batch_length_mismatch_raises_error(
    chroma_store: ChromaVectorStore,
) -> None:
    """Mismatched array lengths raise IndexingError with appropriate error code."""
    with pytest.raises(IndexingError) as exc_info:
        chroma_store.upsert_chunks(
            chunk_ids=["c1"],
            embeddings=[[0.1] * 384],
            metadatas=[],  # empty!
            documents=["text"],
        )
    assert exc_info.value.code == "VECTOR_BATCH_LENGTH_MISMATCH"


def test_chroma_persists_across_reinitialization(tmp_path: Path) -> None:
    """Vectors written to disk remain available to a fresh ChromaVectorStore client."""
    persist_dir = tmp_path / "chroma_persist_restart"

    store_1 = ChromaVectorStore(
        persist_path=persist_dir,
        collection_name="persist_check",
    )
    store_1.upsert_chunks(
        chunk_ids=["v1_c0", "v1_c1"],
        embeddings=[[0.1] * 384, [0.2] * 384],
        metadatas=[
            {"document_version_id": "v1", "chunk_index": 0, "department_id": ""},
            {"document_version_id": "v1", "chunk_index": 1, "department_id": ""},
        ],
        documents=["Chunk zero", "Chunk one"],
    )
    assert store_1.count_by_version("v1") == 2

    # Create a brand new client pointing at the same local directory
    store_2 = ChromaVectorStore(
        persist_path=persist_dir,
        collection_name="persist_check",
    )
    assert store_2.count_by_version("v1") == 2
    assert store_2.get_collection_count() == 2
