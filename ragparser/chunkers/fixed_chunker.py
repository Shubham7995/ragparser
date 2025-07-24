"""
Fixed-size chunking strategy
"""

from typing import List
import re

from .base import BaseChunker
from ..core.models import ParsedDocument, ParserConfig, ChunkResult


class FixedChunker(BaseChunker):
    """Fixed-size chunking with overlap"""

    async def chunk_async(
        self, document: ParsedDocument, config: ParserConfig
    ) -> List[ChunkResult]:
        """
        Chunk document using fixed-size strategy

        Args:
            document: Parsed document to chunk
            config: Parser configuration

        Returns:
            List of chunk results
        """
        chunks = []
        content = document.content
        chunk_size = config.chunk_size
        overlap = config.chunk_overlap

        if not content.strip():
            return chunks

        # Split content into sentences for better chunk boundaries
        sentences = self._split_into_sentences(content)

        current_chunk = ""
        current_sentences = []
        start_char = 0

        for i, sentence in enumerate(sentences):
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk + sentence) > chunk_size and current_chunk:
                # Create chunk from current content
                chunk_content = self._clean_chunk_content(current_chunk)
                if chunk_content:
                    chunks.append(
                        self._create_chunk(
                            content=chunk_content,
                            source_blocks=list(range(len(document.content_blocks))),
                            metadata={
                                "chunk_method": "fixed",
                                "sentence_count": len(current_sentences),
                                "overlap_chars": overlap,
                            },
                            start_char=start_char,
                            end_char=start_char + len(current_chunk),
                        )
                    )

                # Start new chunk with overlap
                if overlap > 0 and chunks:
                    overlap_text = self._get_overlap_text(current_chunk, overlap)
                    current_chunk = overlap_text + sentence
                    start_char = start_char + len(current_chunk) - len(overlap_text)
                else:
                    current_chunk = sentence
                    start_char = start_char + len(current_chunk)

                current_sentences = [sentence]
            else:
                current_chunk += sentence
                current_sentences.append(sentence)

        # Add final chunk
        if current_chunk.strip():
            chunk_content = self._clean_chunk_content(current_chunk)
            chunks.append(
                self._create_chunk(
                    content=chunk_content,
                    source_blocks=list(range(len(document.content_blocks))),
                    metadata={
                        "chunk_method": "fixed",
                        "sentence_count": len(current_sentences),
                        "is_final": True,
                    },
                    start_char=start_char,
                    end_char=start_char + len(current_chunk),
                )
            )

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex"""
        # Pattern to split on sentence endings, but preserve them
        pattern = r"(?<=[.!?])\s+"
        sentences = re.split(pattern, text)

        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                if not sentence.endswith((".", "!", "?")):
                    sentence += " "
                cleaned_sentences.append(sentence)

        return cleaned_sentences

    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text from end of current chunk"""
        if len(text) <= overlap_size:
            return text

        # Try to find a good break point (space, sentence end)
        overlap_text = text[-overlap_size:]

        # Find the last sentence boundary in overlap
        for i in range(len(overlap_text) - 1, 0, -1):
            if overlap_text[i] in ".!?":
                return overlap_text[i + 1 :].strip() + " "

        # Find the last word boundary
        for i in range(len(overlap_text) - 1, 0, -1):
            if overlap_text[i] == " ":
                return overlap_text[i + 1 :].strip() + " "

        return overlap_text
