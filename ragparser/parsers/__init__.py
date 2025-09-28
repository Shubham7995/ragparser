"""
Document parsers for different file formats
"""

from typing import Optional, Dict, Type
from ..core.models import FileType
from .base import BaseParser

# Import parsers with optional dependencies
_PARSERS: Dict[FileType, Type[BaseParser]] = {}

# Always available parsers first
from .text_parser import TextParser
from .html_parser import HTMLParser

_PARSERS[FileType.TXT] = TextParser
_PARSERS[FileType.MD] = TextParser
_PARSERS[FileType.HTML] = HTMLParser
_PARSERS[FileType.CSV] = TextParser
_PARSERS[FileType.JSON] = TextParser

# Optional parsers - only import if dependencies are available
try:
    from .pdf_parser import PDFParser

    _PARSERS[FileType.PDF] = PDFParser
except ImportError:
    pass

try:
    from .docx_parser import DOCXParser

    _PARSERS[FileType.DOCX] = DOCXParser
except ImportError:
    pass

try:
    from .pptx_parser import PPTXParser

    _PARSERS[FileType.PPTX] = PPTXParser
except ImportError:
    pass

try:
    from .xlsx_parser import XLSXParser

    _PARSERS[FileType.XLSX] = XLSXParser
except ImportError:
    pass

try:
    from .image_parser import ImageParser

    _PARSERS[FileType.IMAGE] = ImageParser
except ImportError:
    pass


def get_parser(file_type: FileType) -> Optional[BaseParser]:
    """
    Get parser instance for given file type

    Args:
        file_type: The file type to get parser for

    Returns:
        Parser instance or None if not supported
    """
    parser_class = _PARSERS.get(file_type)
    if parser_class:
        return parser_class()
    return None


def get_supported_formats() -> list[FileType]:
    """Get list of supported file formats"""
    return list(_PARSERS.keys())


def is_format_supported(file_type: FileType) -> bool:
    """Check if file format is supported"""
    return file_type in _PARSERS


__all__ = ["BaseParser", "get_parser", "get_supported_formats", "is_format_supported"]
