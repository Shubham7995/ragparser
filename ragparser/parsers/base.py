"""
Base parser class for all document parsers
"""

from abc import ABC, abstractmethod
from typing import Union, Optional
from pathlib import Path

from ..core.models import ParsedDocument, ParserConfig, FileType


class BaseParser(ABC):
    """Base class for all document parsers"""

    def __init__(self):
        self.supported_formats = []

    @abstractmethod
    async def parse_async(
        self, file_path: Path, config: ParserConfig
    ) -> ParsedDocument:
        """
        Parse document from file path asynchronously

        Args:
            file_path: Path to the file
            config: Parser configuration

        Returns:
            ParsedDocument with extracted content
        """
        pass

    @abstractmethod
    async def parse_from_bytes_async(
        self, data: bytes, filename: str, config: ParserConfig
    ) -> ParsedDocument:
        """
        Parse document from bytes asynchronously

        Args:
            data: File data as bytes
            filename: Original filename
            config: Parser configuration

        Returns:
            ParsedDocument with extracted content
        """
        pass

    def can_parse(self, file_type: FileType) -> bool:
        """Check if this parser can handle the given file type"""
        return file_type in self.supported_formats

    async def _create_base_document(
        self,
        file_path: Optional[Path],
        filename: str,
        file_type: FileType,
        file_size: int,
    ) -> ParsedDocument:
        """Create base document structure"""
        from ..core.models import DocumentMetadata
        from datetime import datetime

        metadata = DocumentMetadata(
            file_name=filename,
            file_type=file_type,
            file_size=file_size,
            creation_date=(
                datetime.now()
                if not file_path
                else datetime.fromtimestamp(file_path.stat().st_ctime)
            ),
            modification_date=(
                datetime.now()
                if not file_path
                else datetime.fromtimestamp(file_path.stat().st_mtime)
            ),
        )

        return ParsedDocument(content="", metadata=metadata)
