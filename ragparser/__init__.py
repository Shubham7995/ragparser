"""
RAG Parser - A comprehensive data parser for RAG applications
"""

from .core.parser import RagParser
from .core.models import (
    ParsedDocument,
    ChunkResult,
    ParserConfig,
    ParsingResult,
    DocumentMetadata,
    ContentBlock,
    FileType,
    ChunkingStrategy,
)
from .core.exceptions import (
    ParserError,
    UnsupportedFormatError,
    ProcessingError,
    FileSizeError,
    ContentExtractionError,
    ChunkingError,
    MetadataExtractionError,
)

__version__ = "1.0.5"
__author__ = "Shubham Shinde"
__email__ = "shubhamshinde7995@gmail.com"

__all__ = [
    # Main parser class
    "RagParser",
    # Core data models
    "ParsedDocument",
    "ChunkResult",
    "ParserConfig",
    "ParsingResult",
    "DocumentMetadata",
    "ContentBlock",
    # Enums
    "FileType",
    "ChunkingStrategy",
    # Exceptions
    "ParserError",
    "UnsupportedFormatError",
    "ProcessingError",
    "FileSizeError",
    "ContentExtractionError",
    "ChunkingError",
    "MetadataExtractionError",
]
