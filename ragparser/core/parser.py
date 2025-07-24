"""
Main RAG parser class
"""

import asyncio
import os
import time
from typing import Union, Optional, List
from pathlib import Path

from .models import (
    ParsedDocument,
    ParserConfig,
    ParsingResult,
    FileType,
    ChunkingStrategy,
)
from .exceptions import UnsupportedFormatError, FileSizeError, ProcessingError
from ..utils.file_detector import FileDetector
from ..parsers import get_parser
from ..chunkers import get_chunker
from ..processors.metadata_extractor import MetadataExtractor
from ..processors.content_cleaner import ContentCleaner
from ..processors.embedding_prep import EmbeddingPreprocessor


class RagParser:
    """
    Main RAG parser for processing documents into RAG-ready format
    """

    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize the RAG parser

        Args:
            config: Parser configuration, uses defaults if None
        """
        self.config = config or ParserConfig()
        self.file_detector = FileDetector()
        self.metadata_extractor = MetadataExtractor()
        self.content_cleaner = ContentCleaner()
        self.embedding_preprocessor = EmbeddingPreprocessor()

    def parse(self, file_path: Union[str, Path]) -> ParsingResult:
        """
        Parse a document synchronously

        Args:
            file_path: Path to the file to parse

        Returns:
            ParsingResult with parsed document or error
        """
        return asyncio.run(self.parse_async(file_path))

    async def parse_async(self, file_path: Union[str, Path]) -> ParsingResult:
        """
        Parse a document asynchronously

        Args:
            file_path: Path to the file to parse

        Returns:
            ParsingResult with parsed document or error
        """
        start_time = time.time()
        file_path = Path(file_path)

        try:
            # Validate file
            await self._validate_file(file_path)

            # Detect file type
            file_type = self.file_detector.detect_type(file_path)

            # Get appropriate parser
            parser = get_parser(file_type)
            if not parser:
                raise UnsupportedFormatError(file_type.value)

            # Parse document
            document = await parser.parse_async(file_path, self.config)

            # Extract metadata if enabled
            if self.config.extract_metadata:
                document.metadata = await self.metadata_extractor.extract_async(
                    file_path, document, self.config
                )

            # Clean content if enabled
            if self.config.clean_text:
                document = await self.content_cleaner.clean_async(document, self.config)

            # Chunk content if strategy is not NONE
            if self.config.chunking_strategy != ChunkingStrategy.NONE:
                chunker = get_chunker(self.config.chunking_strategy)
                document.chunks = await chunker.chunk_async(document, self.config)

            # Prepare for embedding
            document = await self.embedding_preprocessor.process_async(
                document, self.config
            )

            # Calculate processing time
            processing_time = time.time() - start_time
            document.processing_time = processing_time

            return ParsingResult(
                success=True,
                document=document,
                processing_stats={
                    "processing_time": processing_time,
                    "file_size": file_path.stat().st_size,
                    "content_length": len(document.content),
                    "chunk_count": len(document.chunks),
                    "block_count": len(document.content_blocks),
                },
            )

        except Exception as e:
            processing_time = time.time() - start_time
            return ParsingResult(
                success=False,
                error=str(e),
                processing_stats={
                    "processing_time": processing_time,
                    "error_type": type(e).__name__,
                },
            )

    def parse_multiple(self, file_paths: List[Union[str, Path]]) -> List[ParsingResult]:
        """
        Parse multiple documents synchronously

        Args:
            file_paths: List of file paths to parse

        Returns:
            List of ParsingResults
        """
        return asyncio.run(self.parse_multiple_async(file_paths))

    async def parse_multiple_async(
        self, file_paths: List[Union[str, Path]]
    ) -> List[ParsingResult]:
        """
        Parse multiple documents asynchronously with concurrency

        Args:
            file_paths: List of file paths to parse

        Returns:
            List of ParsingResults
        """
        tasks = [self.parse_async(path) for path in file_paths]
        return await asyncio.gather(*tasks, return_exceptions=False)

    def parse_from_bytes(self, data: bytes, filename: str) -> ParsingResult:
        """
        Parse document from bytes

        Args:
            data: File data as bytes
            filename: Original filename for type detection

        Returns:
            ParsingResult
        """
        return asyncio.run(self.parse_from_bytes_async(data, filename))

    async def parse_from_bytes_async(self, data: bytes, filename: str) -> ParsingResult:
        """
        Parse document from bytes asynchronously

        Args:
            data: File data as bytes
            filename: Original filename for type detection

        Returns:
            ParsingResult
        """
        start_time = time.time()

        try:
            # Validate data size
            if len(data) > self.config.max_file_size:
                raise FileSizeError(len(data), self.config.max_file_size)

            # Detect file type
            file_type = self.file_detector.detect_type_from_bytes(data, filename)

            # Get appropriate parser
            parser = get_parser(file_type)
            if not parser:
                raise UnsupportedFormatError(file_type.value)

            # Parse document from bytes
            document = await parser.parse_from_bytes_async(data, filename, self.config)

            # Process similar to file parsing
            if self.config.clean_text:
                document = await self.content_cleaner.clean_async(document, self.config)

            if self.config.chunking_strategy != ChunkingStrategy.NONE:
                chunker = get_chunker(self.config.chunking_strategy)
                document.chunks = await chunker.chunk_async(document, self.config)

            document = await self.embedding_preprocessor.process_async(
                document, self.config
            )

            processing_time = time.time() - start_time
            document.processing_time = processing_time

            return ParsingResult(
                success=True,
                document=document,
                processing_stats={
                    "processing_time": processing_time,
                    "file_size": len(data),
                    "content_length": len(document.content),
                    "chunk_count": len(document.chunks),
                },
            )

        except Exception as e:
            processing_time = time.time() - start_time
            return ParsingResult(
                success=False,
                error=str(e),
                processing_stats={
                    "processing_time": processing_time,
                    "error_type": type(e).__name__,
                },
            )

    async def _validate_file(self, file_path: Path) -> None:
        """Validate file exists and size"""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        file_size = file_path.stat().st_size
        if file_size > self.config.max_file_size:
            raise FileSizeError(file_size, self.config.max_file_size)

        if file_size == 0:
            raise ValueError(f"File is empty: {file_path}")

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return [ft.value for ft in FileType]

    def update_config(self, **kwargs) -> None:
        """Update parser configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                self.config.custom_settings[key] = value
