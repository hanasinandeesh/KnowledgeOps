import hashlib
import re
from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.modules.indexing.schemas import TextChunk


def default_token_counter(text: str) -> int:
    """Fast, reliable token counter for chunking when model tokenizer is not injected.

    Uses whitespace and punctuation boundaries (~1.3 tokens per whitespace word).
    """
    if not text.strip():
        return 0
    words = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
    return len(words)


class TextChunker:
    """Structure-aware hierarchical document text chunker.

    Preserves document structure (page numbers, headings, section context)
    and segments text respecting paragraph and sentence boundaries.
    """

    def __init__(
        self,
        target_tokens: int | None = None,
        overlap_tokens: int | None = None,
        min_tokens: int | None = None,
        max_tokens: int | None = None,
        token_counter: Callable[[str], int] | None = None,
    ) -> None:
        self.target_tokens = (
            target_tokens if target_tokens is not None else settings.CHUNK_TARGET_TOKENS
        )
        self.overlap_tokens = (
            overlap_tokens
            if overlap_tokens is not None
            else settings.CHUNK_OVERLAP_TOKENS
        )
        self.min_tokens = (
            min_tokens if min_tokens is not None else settings.CHUNK_MIN_TOKENS
        )
        self.max_tokens = (
            max_tokens if max_tokens is not None else settings.CHUNK_MAX_TOKENS
        )
        self.count_tokens = token_counter or default_token_counter

    def _split_into_units(self, text: str) -> list[str]:
        """Split text hierarchically into paragraphs, falling back to sentences."""
        raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        units: list[str] = []

        for p in raw_paragraphs:
            p_tokens = self.count_tokens(p)
            if p_tokens <= self.target_tokens:
                units.append(p)
            else:
                # Paragraph is larger than target; split into sentences
                sentences = [
                    s.strip() for s in re.split(r"(?<=[.!?])\s+", p) if s.strip()
                ]
                for s in sentences:
                    s_tokens = self.count_tokens(s)
                    if s_tokens <= self.target_tokens:
                        units.append(s)
                    else:
                        # Sentence is extremely long; split into phrase/clause chunks
                        words = s.split()
                        curr_words: list[str] = []
                        for w in words:
                            curr_words.append(w)
                            if (
                                self.count_tokens(" ".join(curr_words))
                                >= self.target_tokens
                            ):
                                units.append(" ".join(curr_words))
                                curr_words = []
                        if curr_words:
                            units.append(" ".join(curr_words))

        return units

    def chunk_pages(self, pages: list[Any]) -> list[TextChunk]:
        """Chunk a collection of document pages/sections into structured TextChunks.

        Accepts any iterable of objects with:
        - text / text_content: str
        - page_number: int | None
        - section_title: str | None
        """
        chunks: list[TextChunk] = []
        global_chunk_index = 0

        for page in pages:
            # Extract content from ExtractedPage or DocumentPage
            raw_text = getattr(page, "text", None)
            if raw_text is None:
                raw_text = getattr(page, "text_content", "")

            text = raw_text.strip()
            if not text:
                continue

            page_number = getattr(page, "page_number", None)
            section_title = getattr(page, "section_title", None)

            header_prefix = ""
            if section_title:
                header_prefix = f"[Section: {section_title}]\n"

            header_tokens = self.count_tokens(header_prefix)
            units = self._split_into_units(text)
            if not units:
                continue

            section_chunks: list[str] = []
            curr_units: list[str] = []
            curr_tokens = header_tokens

            for unit in units:
                unit_tokens = self.count_tokens(unit)

                if curr_units and (curr_tokens + unit_tokens > self.target_tokens):
                    # Finalize current chunk
                    chunk_text = "\n\n".join(curr_units)
                    if header_prefix and not chunk_text.startswith(
                        header_prefix.strip()
                    ):
                        chunk_text = f"{header_prefix}{chunk_text}"
                    section_chunks.append(chunk_text)

                    # Build overlap from trailing units
                    overlap_units: list[str] = []
                    overlap_count = 0
                    for u in reversed(curr_units):
                        u_t = self.count_tokens(u)
                        if overlap_count + u_t <= self.overlap_tokens:
                            overlap_units.insert(0, u)
                            overlap_count += u_t
                        else:
                            break

                    curr_units = list(overlap_units)
                    curr_tokens = header_tokens + overlap_count

                curr_units.append(unit)
                curr_tokens += unit_tokens

            # Append any remaining units
            if curr_units:
                chunk_text = "\n\n".join(curr_units)
                if header_prefix and not chunk_text.startswith(header_prefix.strip()):
                    chunk_text = f"{header_prefix}{chunk_text}"
                section_chunks.append(chunk_text)

            # Post-process: merge tiny trailing chunk if below min_tokens
            if (
                len(section_chunks) > 1
                and self.count_tokens(section_chunks[-1]) < self.min_tokens
            ):
                combined = f"{section_chunks[-2]}\n\n{section_chunks[-1]}"
                if self.count_tokens(combined) <= self.max_tokens:
                    section_chunks.pop()
                    section_chunks[-1] = combined

            # Generate final TextChunk objects
            for chunk_content in section_chunks:
                clean_content = chunk_content.strip()
                if not clean_content:
                    continue

                token_count = self.count_tokens(clean_content)
                content_hash = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()

                chunks.append(
                    TextChunk(
                        chunk_index=global_chunk_index,
                        content=clean_content,
                        content_hash=content_hash,
                        page_number=page_number,
                        section_title=section_title,
                        token_count=token_count,
                    )
                )
                global_chunk_index += 1

        return chunks
