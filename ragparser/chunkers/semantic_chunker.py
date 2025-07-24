"""
Semantic chunking strategy based on content structure
"""

from typing import List, Dict, Any
import re

from .base import BaseChunker
from ..core.models import ParsedDocument, ParserConfig, ChunkResult, ContentBlock


class SemanticChunker(BaseChunker):
    """Semantic chunking based on document structure and content"""

    async def chunk_async(
        self, document: ParsedDocument, config: ParserConfig
    ) -> List[ChunkResult]:
        """
        Chunk document using semantic strategy

        Args:
            document: Parsed document to chunk
            config: Parser configuration

        Returns:
            List of chunk results
        """
        chunks = []

        if not document.content_blocks:
            # Fallback to simple text chunking
            return await self._chunk_plain_text(document, config)

        # Group content blocks by semantic meaning
        semantic_groups = self._group_blocks_semantically(
            document.content_blocks, config
        )

        for group_idx, group in enumerate(semantic_groups):
            chunk_content = self._combine_blocks(group["blocks"])

            if chunk_content.strip():
                # Check if chunk is too large and needs splitting
                if len(chunk_content) > config.chunk_size * 1.5:
                    sub_chunks = await self._split_large_chunk(
                        chunk_content, group["blocks"], config
                    )
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(
                        self._create_chunk(
                            content=self._clean_chunk_content(chunk_content),
                            source_blocks=[block["index"] for block in group["blocks"]],
                            metadata={
                                "chunk_method": "semantic",
                                "semantic_type": group["type"],
                                "block_count": len(group["blocks"]),
                                "group_index": group_idx,
                            },
                        )
                    )

        return chunks

    def _group_blocks_semantically(
        self, content_blocks: List[ContentBlock], config: ParserConfig
    ) -> List[Dict[str, Any]]:
        """Group content blocks by semantic meaning"""
        groups = []
        current_group = {"type": "content", "blocks": []}

        for i, block in enumerate(content_blocks):
            block_info = {"block": block, "index": i, "content": block.content}

            # Determine if this block starts a new semantic group
            if self._should_start_new_group(block, current_group, config):
                # Save current group if it has content
                if current_group["blocks"]:
                    groups.append(current_group)

                # Start new group
                current_group = {
                    "type": self._get_semantic_type(block),
                    "blocks": [block_info],
                }
            else:
                current_group["blocks"].append(block_info)

        # Add final group
        if current_group["blocks"]:
            groups.append(current_group)

        return groups

    def _should_start_new_group(
        self, block: ContentBlock, current_group: Dict[str, Any], config: ParserConfig
    ) -> bool:
        """Determine if a block should start a new semantic group"""

        # Always start new group for headers
        if block.block_type.startswith("header"):
            return True

        # Start new group for different content types
        semantic_type = self._get_semantic_type(block)
        if semantic_type != current_group["type"]:
            return True

        # Start new group if current group is getting too large
        current_size = sum(len(b["content"]) for b in current_group["blocks"])
        if current_size + len(block.content) > config.chunk_size:
            return True

        # Check for topic shifts in text content
        if block.block_type == "text" and current_group["blocks"]:
            if self._detect_topic_shift(block, current_group["blocks"][-1]["block"]):
                return True

        return False

    def _get_semantic_type(self, block: ContentBlock) -> str:
        """Get semantic type for a content block"""
        if block.block_type.startswith("header"):
            return "header"
        elif block.block_type == "table":
            return "table"
        elif block.block_type in ["code", "quote"]:
            return block.block_type
        elif block.block_type in ["list", "list_item"]:
            return "list"
        else:
            return "content"

    def _detect_topic_shift(
        self, current_block: ContentBlock, previous_block: ContentBlock
    ) -> bool:
        """Detect potential topic shifts between blocks"""
        current_text = current_block.content.lower()
        previous_text = previous_block.content.lower()

        # Look for topic shift indicators
        topic_indicators = [
            "however",
            "meanwhile",
            "furthermore",
            "in contrast",
            "on the other hand",
            "in addition",
            "moreover",
            "nevertheless",
            "consequently",
            "therefore",
            "in conclusion",
            "to summarize",
            "next",
            "first",
            "second",
            "third",
            "finally",
            "lastly",
        ]

        # Check if current block starts with topic indicator
        for indicator in topic_indicators:
            if current_text.startswith(indicator):
                return True

        # Check for significant vocabulary change (simple heuristic)
        current_words = set(re.findall(r"\b\w+\b", current_text))
        previous_words = set(re.findall(r"\b\w+\b", previous_text))

        if len(current_words) > 5 and len(previous_words) > 5:
            overlap = len(current_words.intersection(previous_words))
            total = len(current_words.union(previous_words))
            overlap_ratio = overlap / total if total > 0 else 0

            # If vocabulary overlap is very low, might be topic shift
            if overlap_ratio < 0.1:
                return True

        return False

    def _combine_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Combine blocks into chunk content"""
        parts = []

        for block_info in blocks:
            block = block_info["block"]
            content = block.content.strip()

            if block.block_type.startswith("header"):
                # Format headers
                level = (
                    block.formatting.get("header_level", 1) if block.formatting else 1
                )
                prefix = "#" * level + " "
                parts.append(f"{prefix}{content}")
            elif block.block_type == "quote":
                parts.append(f"> {content}")
            elif block.block_type == "code":
                parts.append(f"```\n{content}\n```")
            elif block.block_type == "list_item":
                parts.append(f"• {content}")
            else:
                parts.append(content)

        return "\n\n".join(parts)

    async def _split_large_chunk(
        self, content: str, blocks: List[Dict[str, Any]], config: ParserConfig
    ) -> List[ChunkResult]:
        """Split large semantic chunk into smaller chunks"""
        chunks = []

        # Try to split at paragraph boundaries first
        paragraphs = content.split("\n\n")

        current_chunk = ""
        current_blocks = []

        for i, paragraph in enumerate(paragraphs):
            if len(current_chunk + paragraph) > config.chunk_size and current_chunk:
                # Create chunk
                chunks.append(
                    self._create_chunk(
                        content=self._clean_chunk_content(current_chunk),
                        source_blocks=[b["index"] for b in current_blocks],
                        metadata={
                            "chunk_method": "semantic_split",
                            "part_of_larger_section": True,
                            "split_method": "paragraph",
                        },
                    )
                )

                current_chunk = paragraph
                current_blocks = blocks  # Approximate - all blocks contribute
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_blocks = blocks

        # Add final chunk
        if current_chunk.strip():
            chunks.append(
                self._create_chunk(
                    content=self._clean_chunk_content(current_chunk),
                    source_blocks=[b["index"] for b in current_blocks],
                    metadata={
                        "chunk_method": "semantic_split",
                        "part_of_larger_section": True,
                        "split_method": "paragraph",
                        "is_final": True,
                    },
                )
            )

        return chunks

    async def _chunk_plain_text(
        self, document: ParsedDocument, config: ParserConfig
    ) -> List[ChunkResult]:
        """Fallback chunking for plain text without structure"""
        from .fixed_chunker import FixedChunker

        # Use fixed chunker as fallback
        fixed_chunker = FixedChunker()
        chunks = await fixed_chunker.chunk_async(document, config)

        # Update metadata to indicate semantic fallback
        for chunk in chunks:
            chunk.metadata.update(
                {
                    "chunk_method": "semantic_fallback",
                    "fallback_reason": "no_content_blocks",
                }
            )

        return chunks
