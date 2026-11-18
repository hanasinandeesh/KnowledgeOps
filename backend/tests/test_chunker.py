from app.modules.indexing.chunker import TextChunker
from app.modules.ingestion.schemas import ExtractedPage


def test_chunker_basic_chunking() -> None:
    """Test basic chunking respects target token boundaries and indices."""
    chunker = TextChunker(target_tokens=50, overlap_tokens=10, min_tokens=10)
    pages = [
        ExtractedPage(
            page_number=1,
            section_title="Introduction",
            text="This is the first sentence. This is the second sentence. "
            "This is the third sentence that provides more details on the topic. "
            "Here is another sentence continuing the policy explanation.",
            char_count=200,
        )
    ]

    chunks = chunker.chunk_pages(pages)
    assert len(chunks) >= 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_number == 1
    assert chunks[0].section_title == "Introduction"
    assert chunks[0].content_hash is not None
    assert len(chunks[0].content_hash) == 64
    assert "[Section: Introduction]" in chunks[0].content


def test_chunker_multi_page_pdf_preserves_page_numbers() -> None:
    """Test multi-page document chunks preserve originating page numbers."""
    chunker = TextChunker(target_tokens=30, overlap_tokens=5, min_tokens=5)
    pages = [
        ExtractedPage(
            page_number=1,
            section_title=None,
            text="First page content discussing Acme company structure and teams.",
            char_count=65,
        ),
        ExtractedPage(
            page_number=2,
            section_title=None,
            text="Second page content covering expense reimbursement rates and limits.",
            char_count=75,
        ),
    ]

    chunks = chunker.chunk_pages(pages)
    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert "First page" in chunks[0].content

    assert chunks[1].page_number == 2
    assert chunks[1].chunk_index == 1
    assert "Second page" in chunks[1].content


def test_chunker_merges_small_trailing_chunk() -> None:
    """Test that tiny trailing chunks below min_tokens merge into preceding chunk."""
    chunker = TextChunker(
        target_tokens=20,
        overlap_tokens=0,
        min_tokens=10,
        max_tokens=100,
    )
    pages = [
        ExtractedPage(
            page_number=1,
            section_title="Policy",
            text=(
                "Paragraph one with several words to fill up the target budget.\n\n"
                "Tiny end."
            ),
            char_count=90,
        )
    ]

    chunks = chunker.chunk_pages(pages)
    # "Tiny end." (2 words) should be merged into the previous chunk
    assert len(chunks) == 1
    assert "Tiny end." in chunks[0].content


def test_chunker_empty_pages_handled_safely() -> None:
    """Test empty pages produce zero chunks without error."""
    chunker = TextChunker()
    assert chunker.chunk_pages([]) == []
    assert (
        chunker.chunk_pages(
            [ExtractedPage(page_number=1, section_title=None, text="   ", char_count=0)]
        )
        == []
    )


def test_chunker_deterministic_hashes() -> None:
    """Test that identical text produces identical hashes and token counts."""
    chunker = TextChunker()
    page = ExtractedPage(
        page_number=1,
        section_title="Fixed",
        text="Consistent text for hashing verification.",
        char_count=42,
    )

    chunks_1 = chunker.chunk_pages([page])
    chunks_2 = chunker.chunk_pages([page])

    assert chunks_1[0].content_hash == chunks_2[0].content_hash
    assert chunks_1[0].token_count == chunks_2[0].token_count
    assert chunks_1[0].content == chunks_2[0].content
