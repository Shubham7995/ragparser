"""
Core data models for RAG parser
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class FileType(Enum):
    """Supported file types"""

    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    IMAGE = "image"
    CSV = "csv"
    JSON = "json"


class ChunkingStrategy(Enum):
    """Available chunking strategies"""

    FIXED = "fixed"
    SEMANTIC = "semantic"
    ADAPTIVE = "adaptive"
    NONE = "none"


@dataclass
class DocumentMetadata:
    """Metadata extracted from documents"""

    file_name: str
    file_type: FileType
    file_size: int
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    language: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    character_count: Optional[int] = None
    custom_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentBlock:
    """A block of content with type and metadata"""

    content: str
    block_type: str  # text, table, image, header, etc.
    page_number: Optional[int] = None
    position: Optional[Dict[str, float]] = None  # x, y, width, height
    formatting: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None


@dataclass
class ChunkResult:
    """Result of chunking operation"""

    content: str
    chunk_id: str
    source_blocks: List[int]  # indices of ContentBlocks
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding_ready: bool = True
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    token_count: Optional[int] = None


@dataclass
class ParsedDocument:
    """Complete parsed document result"""

    content: str
    metadata: DocumentMetadata
    content_blocks: List[ContentBlock] = field(default_factory=list)
    chunks: List[ChunkResult] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    processing_time: Optional[float] = None
    quality_score: Optional[float] = None
    extraction_notes: List[str] = field(default_factory=list)


@dataclass
class ParserConfig:
    """Configuration for parsing operations"""

    # Chunking settings
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # OCR settings
    enable_ocr: bool = True
    ocr_language: str = "eng"
    ocr_confidence_threshold: float = 0.7

    # Content extraction
    extract_tables: bool = True
    extract_images: bool = True
    extract_metadata: bool = True
    extract_links: bool = True

    # Processing options
    clean_text: bool = True
    preserve_formatting: bool = False
    extract_headers: bool = True
    merge_paragraphs: bool = True

    # Performance settings
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    timeout_seconds: int = 300

    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsingResult:
    """Result of a parsing operation with status"""

    success: bool
    document: Optional[ParsedDocument] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    processing_stats: Dict[str, Any] = field(default_factory=dict)
