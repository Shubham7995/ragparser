"""
Adaptive chunking strategy that adjusts based on content
"""

from typing import List, Dict, Any
import re

from .base import BaseChunker
from ..core.models import ParsedDocument, ParserConfig, ChunkResult, ContentBlock


class AdaptiveChunker(BaseChunker):
    """Adaptive chunking that adjusts size based on content characteristics"""

    async def chunk_async(
        self, document: ParsedDocument, config: ParserConfig
    ) -> List[ChunkResult]:
        """
        Chunk document using adaptive strategy

        Args:
            document: Parsed document to chunk
            config: Parser configuration

        Returns:
            List of chunk results
        """
        chunks = []

        if not document.content.strip():
            return chunks

        # Analyze content characteristics
        content_profile = await self._analyze_content(document, config)

        # Use content blocks if available, otherwise fall back to text analysis
        if document.content_blocks:
            chunks = await self._chunk_from_blocks(document, config, content_profile)
        else:
            chunks = await self._chunk_from_text(document, config, content_profile)

        return chunks

    async def _analyze_content(
        self, document: ParsedDocument, config: ParserConfig
    ) -> Dict[str, Any]:
        """Analyze content to determine optimal chunking strategy"""

        content = document.content
        content_blocks = document.content_blocks

        profile = {
            "content_type": "mixed",
            "structure_level": "low",
            "density": "medium",
            "optimal_chunk_size": config.chunk_size,
            "has_clear_sections": False,
            "avg_paragraph_length": 0,
            "header_frequency": 0,
            "list_frequency": 0,
            "table_frequency": 0,
        }

        # Analyze structure from content blocks
        if content_blocks:
            block_types = {}
            for block in content_blocks:
                block_type = block.block_type
                block_types[block_type] = block_types.get(block_type, 0) + 1

            # Determine structure level
            if any(bt.startswith("header") for bt in block_types):
                profile["has_clear_sections"] = True
                profile["structure_level"] = (
                    "high"
                    if len([bt for bt in block_types if bt.startswith("header")]) > 3
                    else "medium"
                )

            # Calculate frequencies
            total_blocks = len(content_blocks)
            profile["header_frequency"] = sum(
                1 for bt in block_types if bt.startswith("header")
            ) / max(total_blocks, 1)
            profile["list_frequency"] = block_types.get("list", 0) + block_types.get(
                "list_item", 0
            ) / max(total_blocks, 1)
            profile["table_frequency"] = block_types.get("table", 0) / max(
                total_blocks, 1
            )

        # Analyze text characteristics
        paragraphs = content.split("\n\n")
        if paragraphs:
            paragraph_lengths = [len(p.strip()) for p in paragraphs if p.strip()]
            if paragraph_lengths:
                profile["avg_paragraph_length"] = sum(paragraph_lengths) / len(
                    paragraph_lengths
                )

        # Determine content type
        if profile["table_frequency"] > 0.2:
            profile["content_type"] = "data_heavy"
        elif profile["header_frequency"] > 0.1:
            profile["content_type"] = "structured"
        elif profile["list_frequency"] > 0.2:
            profile["content_type"] = "enumerated"
        elif profile["avg_paragraph_length"] > 500:
            profile["content_type"] = "narrative"
        else:
            profile["content_type"] = "mixed"

        # Determine density
        words_per_char = len(content.split()) / max(len(content), 1)
        if words_per_char > 0.2:
            profile["density"] = "high"
        elif words_per_char < 0.15:
            profile["density"] = "low"
        else:
            profile["density"] = "medium"

        # Calculate optimal chunk size based on profile
        profile["optimal_chunk_size"] = await self._calculate_optimal_size(
            profile, config
        )

        return profile

    async def _calculate_optimal_size(
        self, profile: Dict[str, Any], config: ParserConfig
    ) -> int:
        """Calculate optimal chunk size based on content profile"""

        base_size = config.chunk_size
        multiplier = 1.0

        # Adjust based on content type
        if profile["content_type"] == "data_heavy":
            multiplier *= 0.7  # Smaller chunks for tables/data
        elif profile["content_type"] == "narrative":
            multiplier *= 1.3  # Larger chunks for continuous text
        elif profile["content_type"] == "structured":
            multiplier *= 1.1  # Slightly larger for well-structured content
        elif profile["content_type"] == "enumerated":
            multiplier *= 0.9  # Slightly smaller for lists

        # Adjust based on structure level
        if profile["structure_level"] == "high":
            multiplier *= 1.2  # Can afford larger chunks with good structure
        elif profile["structure_level"] == "low":
            multiplier *= 0.8  # Smaller chunks for unstructured content

        # Adjust based on density
        if profile["density"] == "high":
            multiplier *= 0.9  # Dense content needs smaller chunks
        elif profile["density"] == "low":
            multiplier *= 1.1  # Sparse content can use larger chunks

        # Adjust based on paragraph length
        if profile["avg_paragraph_length"] > 300:
            multiplier *= 1.1  # Longer paragraphs suggest larger optimal chunks
        elif profile["avg_paragraph_length"] < 100:
            multiplier *= 0.9  # Short paragraphs suggest smaller chunks

        optimal_size = int(base_size * multiplier)

        # Ensure reasonable bounds
        min_size = max(200, base_size // 3)
        max_size = min(3000, base_size * 2)

        return max(min_size, min(max_size, optimal_size))

    async def _chunk_from_blocks(
        self, document: ParsedDocument, config: ParserConfig, profile: Dict[str, Any]
    ) -> List[ChunkResult]:
        """Chunk based on content blocks with adaptive sizing"""

        chunks = []
        current_chunk_blocks = []
        current_chunk_size = 0
        target_size = profile["optimal_chunk_size"]

        for i, block in enumerate(document.content_blocks):
            block_size = len(block.content)

            # Check if we should start a new chunk
            should_split = await self._should_split_at_block(
                block, current_chunk_blocks, current_chunk_size, target_size, profile
            )

            if should_split and current_chunk_blocks:
                # Create chunk from current blocks
                chunk = await self._create_chunk_from_blocks(
                    current_chunk_blocks, document, profile, len(chunks)
                )
                chunks.append(chunk)

                # Start new chunk
                current_chunk_blocks = [block]
                current_chunk_size = block_size
            else:
                # Add to current chunk
                current_chunk_blocks.append(block)
                current_chunk_size += block_size

        # Create final chunk
        if current_chunk_blocks:
            chunk = await self._create_chunk_from_blocks(
                current_chunk_blocks, document, profile, len(chunks)
            )
            chunks.append(chunk)

        return chunks

    async def _should_split_at_block(
        self,
        block: ContentBlock,
        current_blocks: List[ContentBlock],
        current_size: int,
        target_size: int,
        profile: Dict[str, Any],
    ) -> bool:
        """Determine if we should split before this block"""

        if not current_blocks:
            return False

        block_size = len(block.content)

        # Always split at major headers
        if block.block_type in ["header_1", "title"]:
            return True

        # Split at section headers if chunk is getting large
        if block.block_type.startswith("header") and current_size > target_size * 0.6:
            return True

        # Split if adding this block would exceed target by too much
        if current_size + block_size > target_size * 1.5:
            return True

        # Split at natural boundaries for different content types
        if profile["content_type"] == "structured":
            # Split at any header for structured content
            if block.block_type.startswith("header"):
                return True

        elif profile["content_type"] == "data_heavy":
            # Split before/after tables
            if block.block_type == "table" or (
                current_blocks and current_blocks[-1].block_type == "table"
            ):
                return True

        elif profile["content_type"] == "enumerated":
            # Split at major list boundaries
            if (
                block.block_type == "list"
                and current_blocks
                and current_blocks[-1].block_type != "list_item"
            ):
                return True

        # Check for topic shift indicators
        if await self._detect_topic_shift(block, current_blocks[-1]):
            return (
                current_size > target_size * 0.5
            )  # Only split if chunk is reasonably sized

        return False

    async def _detect_topic_shift(
        self, current_block: ContentBlock, previous_block: ContentBlock
    ) -> bool:
        """Detect potential topic shifts between blocks"""

        # Simple topic shift detection
        current_text = current_block.content.lower()
        previous_text = previous_block.content.lower()

        # Look for transition words
        transition_words = [
            "however",
            "meanwhile",
            "furthermore",
            "moreover",
            "nevertheless",
            "consequently",
            "therefore",
            "in contrast",
            "on the other hand",
            "in addition",
            "next",
            "finally",
            "in conclusion",
            "to summarize",
        ]

        for word in transition_words:
            if current_text.startswith(word):
                return True

        # Check for significant vocabulary change (simple heuristic)
        if len(current_text) > 50 and len(previous_text) > 50:
            current_words = set(re.findall(r"\b\w+\b", current_text))
            previous_words = set(re.findall(r"\b\w+\b", previous_text))

            if len(current_words) > 5 and len(previous_words) > 5:
                overlap = len(current_words.intersection(previous_words))
                total_unique = len(current_words.union(previous_words))
                overlap_ratio = overlap / max(total_unique, 1)

                # Low overlap might indicate topic shift
                if overlap_ratio < 0.15:
                    return True

        return False

    async def _create_chunk_from_blocks(
        self,
        blocks: List[ContentBlock],
        document: ParsedDocument,
        profile: Dict[str, Any],
        chunk_index: int,
    ) -> ChunkResult:
        """Create chunk from content blocks"""

        # Combine block content intelligently
        content_parts = []
        block_indices = []

        for i, block in enumerate(blocks):
            content = block.content.strip()

            if block.block_type.startswith("header"):
                # Format headers
                level = (
                    block.formatting.get("header_level", 1) if block.formatting else 1
                )
                content = "#" * level + " " + content
            elif block.block_type == "quote":
                content = "> " + content
            elif block.block_type == "code":
                content = f"```\n{content}\n```"
            elif block.block_type == "list_item":
                content = "• " + content

            content_parts.append(content)

            # Find block index in original document
            for j, doc_block in enumerate(document.content_blocks):
                if (
                    doc_block.content == block.content
                    and doc_block.block_type == block.block_type
                ):
                    block_indices.append(j)
                    break

        # Join content
        combined_content = "\n\n".join(content_parts)

        # Create metadata
        metadata = {
            "chunk_method": "adaptive",
            "content_type": profile["content_type"],
            "structure_level": profile["structure_level"],
            "block_count": len(blocks),
            "optimal_size_used": profile["optimal_chunk_size"],
            "chunk_index": chunk_index,
        }

        return self._create_chunk(
            content=self._clean_chunk_content(combined_content),
            source_blocks=block_indices,
            metadata=metadata,
        )

    async def _chunk_from_text(
        self, document: ParsedDocument, config: ParserConfig, profile: Dict[str, Any]
    ) -> List[ChunkResult]:
        """Fallback chunking from plain text with adaptive sizing"""

        # Use semantic chunker as fallback with adapted size
        from .semantic_chunker import SemanticChunker

        # Temporarily adjust config for adaptive sizing
        adapted_config = ParserConfig(
            chunking_strategy=config.chunking_strategy,
            chunk_size=profile["optimal_chunk_size"],
            chunk_overlap=config.chunk_overlap,
            extract_tables=config.extract_tables,
            extract_images=config.extract_images,
            extract_metadata=config.extract_metadata,
            extract_links=config.extract_links,
            clean_text=config.clean_text,
            preserve_formatting=config.preserve_formatting,
            merge_paragraphs=config.merge_paragraphs,
        )

        semantic_chunker = SemanticChunker()
        chunks = await semantic_chunker.chunk_async(document, adapted_config)

        # Update metadata to indicate adaptive processing
        for chunk in chunks:
            chunk.metadata.update(
                {
                    "chunk_method": "adaptive_fallback",
                    "content_type": profile["content_type"],
                    "structure_level": profile["structure_level"],
                    "optimal_size_used": profile["optimal_chunk_size"],
                    "fallback_reason": "no_content_blocks",
                }
            )

        return chunks
