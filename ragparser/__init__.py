"""
RAG Parser - A comprehensive data parser for RAG applications
"""

from .core.parser import RagParser
from .core.models import ParsedDocument, ChunkResult, ParserConfig
from .core.exceptions import ParserError, UnsupportedFormatError, ProcessingError

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    "RagParser",
    "ParsedDocument",
    "ChunkResult",
    "ParserConfig",
    "ParserError",
    "UnsupportedFormatError",
    "ProcessingError",
]
