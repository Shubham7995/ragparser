"""
Document chunking strategies for RAG
"""

from typing import Optional
from ..core.models import ChunkingStrategy
from .base import BaseChunker
from .fixed_chunker import FixedChunker
from .semantic_chunker import SemanticChunker
from .adaptive_chunker import AdaptiveChunker


_CHUNKERS = {
    ChunkingStrategy.FIXED: FixedChunker,
    ChunkingStrategy.SEMANTIC: SemanticChunker,
    ChunkingStrategy.ADAPTIVE: AdaptiveChunker,
}


def get_chunker(strategy: ChunkingStrategy) -> Optional[BaseChunker]:
    """
    Get chunker instance for given strategy

    Args:
        strategy: The chunking strategy

    Returns:
        Chunker instance or None if not supported
    """
    chunker_class = _CHUNKERS.get(strategy)
    if chunker_class:
        return chunker_class()
    return None


def get_available_strategies() -> list[ChunkingStrategy]:
    """Get list of available chunking strategies"""
    return list(_CHUNKERS.keys())


__all__ = [
    "BaseChunker",
    "FixedChunker",
    "SemanticChunker",
    "AdaptiveChunker",
    "get_chunker",
    "get_available_strategies",
]
