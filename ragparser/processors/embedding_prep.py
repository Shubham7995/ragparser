"""
Embedding preparation processor for RAG optimization
"""

import logging
from typing import List, Dict, Any

from ..core.models import ParsedDocument, ParserConfig, ChunkResult


class EmbeddingPreprocessor:
    """Prepare content for embedding generation"""

    async def process_async(
        self, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """
        Process document for embedding readiness

        Args:
            document: Parsed document
            config: Parser configuration

        Returns:
            Document with embedding-ready chunks
        """
        try:
            # Process chunks for embedding
            if document.chunks:
                document.chunks = await self._process_chunks(
                    document.chunks, document, config
                )

            # Add context information
            document = await self._add_context_metadata(document, config)

            # Validate embedding readiness
            document = await self._validate_embedding_readiness(document, config)

        except Exception as e:
            logging.warning(f"Error in embedding preprocessing: {str(e)}")

        return document

    async def _process_chunks(
        self, chunks: List[ChunkResult], document: ParsedDocument, config: ParserConfig
    ) -> List[ChunkResult]:
        """Process chunks for optimal embedding"""
        processed_chunks = []

        for i, chunk in enumerate(chunks):
            try:
                processed_chunk = await self._process_single_chunk(
                    chunk, document, config, i
                )
                processed_chunks.append(processed_chunk)
            except Exception as e:
                logging.warning(f"Error processing chunk {i}: {str(e)}")
                processed_chunks.append(chunk)  # Keep original if processing fails

        return processed_chunks

    async def _process_single_chunk(
        self,
        chunk: ChunkResult,
        document: ParsedDocument,
        config: ParserConfig,
        chunk_index: int,
    ) -> ChunkResult:
        """Process individual chunk for embedding"""

        # Add context prefix if enabled
        content = chunk.content
        if config.custom_settings.get("add_context_prefix", True):
            content = await self._add_context_prefix(
                content, document, chunk, chunk_index
            )

        # Optimize content for embedding
        content = await self._optimize_for_embedding(content, config)

        # Update chunk metadata
        metadata = chunk.metadata.copy()
        metadata.update(
            {
                "embedding_optimized": True,
                "context_enhanced": config.custom_settings.get(
                    "add_context_prefix", True
                ),
                "embedding_token_estimate": self._estimate_embedding_tokens(content),
            }
        )

        # Check if chunk is suitable for embedding
        embedding_ready = await self._check_embedding_suitability(content, config)

        return ChunkResult(
            content=content,
            chunk_id=chunk.chunk_id,
            source_blocks=chunk.source_blocks,
            metadata=metadata,
            embedding_ready=embedding_ready,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            token_count=self._estimate_tokens(content),
        )

    async def _add_context_prefix(
        self,
        content: str,
        document: ParsedDocument,
        chunk: ChunkResult,
        chunk_index: int,
    ) -> str:
        """Add contextual information to chunk content"""
        context_parts = []

        # Document context
        if document.metadata.title:
            context_parts.append(f"Document: {document.metadata.title}")

        # Section context (from chunk metadata)
        if "semantic_type" in chunk.metadata:
            context_parts.append(f"Section: {chunk.metadata['semantic_type']}")

        # Page context
        if chunk.metadata.get("page_number"):
            context_parts.append(f"Page: {chunk.metadata['page_number']}")

        # Position context
        total_chunks = chunk.metadata.get("total_chunks", 0)
        if total_chunks > 1:
            context_parts.append(f"Part {chunk_index + 1} of {total_chunks}")

        # Combine context with content
        if context_parts:
            context_prefix = " | ".join(context_parts)
            return f"[{context_prefix}]\n\n{content}"

        return content

    async def _optimize_for_embedding(self, content: str, config: ParserConfig) -> str:
        """Optimize content specifically for embedding models"""

        # Remove redundant whitespace
        import re

        content = re.sub(r"\s+", " ", content.strip())

        # Optimize for common embedding model constraints
        max_length = config.custom_settings.get("embedding_max_length", 8000)
        if len(content) > max_length:
            # Truncate intelligently at sentence boundary
            sentences = content.split(".")
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence) <= max_length - 3:
                    truncated += sentence + "."
                else:
                    break

            if truncated:
                content = truncated + "..."
            else:
                content = content[: max_length - 3] + "..."

        # Ensure minimum content length
        min_length = config.custom_settings.get("embedding_min_length", 10)
        if len(content.strip()) < min_length:
            return ""  # Mark as empty if too short

        return content.strip()

    async def _check_embedding_suitability(
        self, content: str, config: ParserConfig
    ) -> bool:
        """Check if content is suitable for embedding"""

        # Check minimum length
        min_length = config.custom_settings.get("embedding_min_length", 10)
        if len(content.strip()) < min_length:
            return False

        # Check maximum length
        max_length = config.custom_settings.get("embedding_max_length", 8000)
        if len(content) > max_length:
            return False

        # Check content quality
        if not await self._is_meaningful_content(content):
            return False

        # Check for embedding-hostile patterns
        if await self._has_embedding_hostile_patterns(content):
            return False

        return True

    async def _is_meaningful_content(self, content: str) -> bool:
        """Check if content is meaningful for embedding"""

        # Remove whitespace for analysis
        clean_content = content.strip()

        if not clean_content:
            return False

        # Check for minimum word count
        words = clean_content.split()
        if len(words) < 3:
            return False

        # Check for reasonable character-to-word ratio
        avg_word_length = len(clean_content.replace(" ", "")) / len(words)
        if (
            avg_word_length < 2 or avg_word_length > 20
        ):  # Suspiciously short or long words
            return False

        # Check for meaningful characters
        alpha_ratio = len([c for c in clean_content if c.isalpha()]) / len(
            clean_content
        )
        if alpha_ratio < 0.3:  # Less than 30% alphabetic characters
            return False

        return True

    async def _has_embedding_hostile_patterns(self, content: str) -> bool:
        """Check for patterns that are problematic for embedding models"""
        import re

        # Very repetitive content
        if len(set(content.split())) / max(len(content.split()), 1) < 0.3:
            return True

        # Excessive special characters
        special_char_ratio = len(re.findall(r"[^\w\s]", content)) / max(len(content), 1)
        if special_char_ratio > 0.5:
            return True

        # Code-like patterns (might not embed well)
        code_patterns = [
            r"\{[^}]*\}",  # Curly braces
            r"<[^>]*>",  # HTML/XML tags
            r"\[[^\]]*\]",  # Square brackets
        ]

        code_matches = 0
        for pattern in code_patterns:
            code_matches += len(re.findall(pattern, content))

        if (
            code_matches / max(len(content.split()), 1) > 0.3
        ):  # Too many code-like patterns
            return True

        return False

    async def _add_context_metadata(
        self, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Add embedding-relevant metadata to document"""

        # Calculate document-level embedding statistics
        embedding_stats = {
            "total_embeddable_chunks": 0,
            "total_embedding_tokens": 0,
            "avg_chunk_tokens": 0,
            "embedding_coverage": 0,
        }

        embeddable_chunks = [c for c in document.chunks if c.embedding_ready]
        embedding_stats["total_embeddable_chunks"] = len(embeddable_chunks)

        if embeddable_chunks:
            token_counts = [c.token_count for c in embeddable_chunks if c.token_count]
            if token_counts:
                embedding_stats["total_embedding_tokens"] = sum(token_counts)
                embedding_stats["avg_chunk_tokens"] = sum(token_counts) / len(
                    token_counts
                )

        # Calculate coverage
        if document.chunks:
            embedding_stats["embedding_coverage"] = len(embeddable_chunks) / len(
                document.chunks
            )

        # Add to document metadata
        document.metadata.custom_metadata.update(
            {
                "embedding_stats": embedding_stats,
                "embedding_ready": embedding_stats["total_embeddable_chunks"] > 0,
            }
        )

        return document

    async def _validate_embedding_readiness(
        self, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Final validation of embedding readiness"""

        # Add quality warnings
        warnings = []

        embeddable_chunks = [c for c in document.chunks if c.embedding_ready]

        if not embeddable_chunks:
            warnings.append("No chunks are suitable for embedding")
        elif len(embeddable_chunks) / max(len(document.chunks), 1) < 0.5:
            warnings.append("Less than 50% of chunks are suitable for embedding")

        # Check average chunk size
        if embeddable_chunks:
            avg_length = sum(len(c.content) for c in embeddable_chunks) / len(
                embeddable_chunks
            )
            if avg_length < 100:
                warnings.append("Average chunk size is very small")
            elif avg_length > 5000:
                warnings.append("Average chunk size is very large")

        # Add warnings to document
        if warnings:
            document.extraction_notes.extend(warnings)

        return document

    def _estimate_embedding_tokens(self, content: str) -> int:
        """Estimate tokens for embedding models (rough approximation)"""
        # Most embedding models use similar tokenization to GPT
        # Rough estimate: ~3.5 characters per token for English text
        return max(1, len(content) // 3)

    def _estimate_tokens(self, content: str) -> int:
        """Estimate general token count"""
        # Simple estimation: ~4 characters per token on average
        return max(1, len(content) // 4)
