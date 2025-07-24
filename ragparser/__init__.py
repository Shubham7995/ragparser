"""
RAG Parser - A comprehensive data parser for RAG applications
"""

from .core.parser import RagParser
from .core.models import ParsedDocument, ChunkResult, ParserConfig
from .core.exceptions import ParserError, UnsupportedFormatError, ProcessingError

__version__ = "1.0.1"
__author__ = "Shubham Shinde"
__email__ = "shubhamshinde7995@gmail.com"

__all__ = [
    "RagParser",
    "ParsedDocument",
    "ChunkResult",
    "ParserConfig",
    "ParserError",
    "UnsupportedFormatError",
    "ProcessingError",
]
