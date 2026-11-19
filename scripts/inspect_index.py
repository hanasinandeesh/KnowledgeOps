"""CLI utility to inspect document chunks, token counts, and local vector embeddings."""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# Add backend directory to sys.path so app imports cleanly
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Ensure Hugging Face operates offline if cached locally
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from app.modules.indexing.chunker import TextChunker
from app.modules.indexing.embeddings import (
    DeterministicMockEmbeddingProvider,
    LocalSentenceTransformerEmbedding,
)
from app.modules.ingestion.extractors import ExtractorFactory


def inspect_all_documents(docs_dir: Path, use_mock: bool = False) -> None:
    """Scan and chunk all documents in the test dataset."""
    chunker = TextChunker()
    files = sorted(docs_dir.rglob("*.*"))
    valid_files = [f for f in files if f.suffix.lower() in [".pdf", ".docx", ".txt"]]

    print("=" * 80)
    print(f"KNOWLEDGEOPS INDEX INSPECTOR: {len(valid_files)} DOCUMENTS")
    print("=" * 80)

    total_chunks = 0
    for f in valid_files:
        dept = f.parent.name.upper()
        extractor = ExtractorFactory.get_extractor(filename=f.name)
        extracted = extractor.extract(f)
        chunks = chunker.chunk_pages(extracted.pages)
        total_chunks += len(chunks)
        print(
            f"[{dept:12}] {f.name:36} -> {len(extracted.pages):2} page(s) -> {len(chunks):2} chunk(s)"
        )

    print("-" * 80)
    print(
        f"TOTAL: {len(valid_files)} documents produced {total_chunks} authoritative chunks.\n"
    )


def inspect_single_document(file_path: Path, use_mock: bool = False) -> None:
    """Extract, chunk, embed, and display a specific document."""
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return

    print("=" * 80)
    print(f"INSPECTING DOCUMENT: {file_path.name}")
    print("=" * 80)

    extractor = ExtractorFactory.get_extractor(filename=file_path.name)
    extracted = extractor.extract(file_path)
    print(f"Extracted {len(extracted.pages)} page(s) / section(s).")

    chunker = TextChunker()
    chunks = chunker.chunk_pages(extracted.pages)
    print(f"Generated {len(chunks)} chunk(s).\n")

    if use_mock:
        embedder = DeterministicMockEmbeddingProvider(dimension=384)
        print("Using DeterministicMockEmbeddingProvider (384 dimensions).")
    else:
        embedder = LocalSentenceTransformerEmbedding()
        print(
            "Using LocalSentenceTransformerEmbedding (BAAI/bge-small-en-v1.5 on CPU)."
        )

    chunk_texts = [c.content for c in chunks]
    embeddings = embedder.embed_documents(chunk_texts)

    for i, chunk in enumerate(chunks):
        emb = embeddings[i]
        print(f"--- [CHUNK #{chunk.chunk_index}] ---")
        print(f"Section Heading : {chunk.section_title or 'None'}")
        print(
            f"Page Number     : {chunk.page_number if chunk.page_number is not None else 'N/A'}"
        )
        print(f"Token Count     : {chunk.token_count}")
        print(f"Content Hash    : {chunk.content_hash[:16]}...")
        print(f"Text Content    :\n{chunk.content}")
        print(f"Embedding Vector: {len(emb)} dimensions (normalized)")
        print(
            f"First 5 floats  : [{emb[0]:.4f}, {emb[1]:.4f}, {emb[2]:.4f}, {emb[3]:.4f}, {emb[4]:.4f}, ...]\n"
        )


def inspect_sqlite(db_path: Path) -> None:
    """Inspect chunks currently persisted in SQLite."""
    print("=" * 80)
    print(f"SQLITE DATABASE: {db_path}")
    print("=" * 80)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM document_chunks")
    count = cur.fetchone()[0]
    print(f"Total chunks stored in 'document_chunks' table: {count}")

    if count > 0:
        cur.execute(
            "SELECT chunk_index, document_version_id, page_number, section_title, token_count, substr(content, 1, 80) FROM document_chunks LIMIT 5"
        )
        for r in cur.fetchall():
            print(
                f"  Chunk #{r[0]} | Version: {r[1][:8]}... | Page: {r[2]} | Tokens: {r[4]}"
            )
            print(f"    Section: {r[3]}")
            print(f"    Text: {r[5]}...\n")
    con.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="KnowledgeOps Index & Chunks Inspector"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to a single document to inspect",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use fast deterministic mock embeddings instead of local transformer model",
    )
    parser.add_argument(
        "--db",
        action="store_true",
        help="Inspect existing SQLite database chunks",
    )
    args = parser.parse_args()

    if args.db:
        inspect_sqlite(Path("data/sqlite/knowledgeops.db"))
    elif args.file:
        inspect_single_document(Path(args.file), use_mock=args.mock)
    else:
        docs_dir = Path("knowledgeops-test-data/documents")
        if docs_dir.exists():
            inspect_all_documents(docs_dir, use_mock=args.mock)
        else:
            print("Documents directory not found.")


if __name__ == "__main__":
    main()
