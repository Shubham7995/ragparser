"""
Base chunker class for document chunking strategies
"""

from abc import ABC, abstractmethod
from typing import List
import uuid

from ..core.models import ParsedDocument, ParserConfig, ChunkResult


class BaseChunker(ABC):
    """Base class for all document chunkers"""

    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    async def chunk_async(
        self, document: ParsedDocument, config: ParserConfig
    ) -> List[ChunkResult]:
        """
        Chunk document content asynchronously

        Args:
            document: Parsed document to chunk
            config: Parser configuration

        Returns:
            List of chunk results
        """
        pass

    def _create_chunk(
        self,
        content: str,
        source_blocks: List[int],
        metadata: dict = None,
        start_char: int = None,
        end_char: int = None,
    ) -> ChunkResult:
        """Create a chunk result"""
        return ChunkResult(
            content=content,
            chunk_id=str(uuid.uuid4()),
            source_blocks=source_blocks,
            metadata=metadata or {},
            start_char=start_char,
            end_char=end_char,
            token_count=self._estimate_token_count(content),
        )

    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Simple estimation: ~4 characters per token on average
        return len(text) // 4

    def _clean_chunk_content(self, content: str) -> str:
        """Clean chunk content"""
        # Remove extra whitespace
        content = " ".join(content.split())
        return content.strip()

    def _validate_chunk_size(self, content: str, max_size: int) -> bool:
        """Check if chunk size is within limits"""
        return len(content) <= max_size
