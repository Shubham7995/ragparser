"""
Custom exceptions for RAG parser
"""


class ParserError(Exception):
    """Base exception for all parser errors"""

    pass


class UnsupportedFormatError(ParserError):
    """Raised when file format is not supported"""

    def __init__(self, file_type: str):
        self.file_type = file_type
        super().__init__(f"Unsupported file format: {file_type}")


class ProcessingError(ParserError):
    """Raised when document processing fails"""

    def __init__(self, message: str, original_error: Exception = None):
        self.original_error = original_error
        super().__init__(message)


class FileSizeError(ParserError):
    """Raised when file is too large"""

    def __init__(self, file_size: int, max_size: int):
        self.file_size = file_size
        self.max_size = max_size
        super().__init__(f"File size {file_size} exceeds maximum {max_size}")


class ContentExtractionError(ParserError):
    """Raised when content extraction fails"""

    pass


class ChunkingError(ParserError):
    """Raised when chunking fails"""

    pass


class MetadataExtractionError(ParserError):
    """Raised when metadata extraction fails"""

    pass
