"""
PDF parser implementation using PyMuPDF (fitz) and pdfplumber
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import io

try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pdfplumber

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from .base import BaseParser
from ..core.models import (
    ParsedDocument,
    ParserConfig,
    FileType,
    ContentBlock,
    DocumentMetadata,
)
from ..core.exceptions import ProcessingError


class PDFParser(BaseParser):
    """Parser for PDF documents"""

    def __init__(self):
        super().__init__()
        self.supported_formats = [FileType.PDF]

        if not (HAS_PYMUPDF or HAS_PDFPLUMBER):
            raise ImportError(
                "PDF parsing requires either PyMuPDF (fitz) or pdfplumber. "
                "Install with: pip install PyMuPDF or pip install pdfplumber"
            )

    async def parse_async(
        self, file_path: Path, config: ParserConfig
    ) -> ParsedDocument:
        """Parse PDF file asynchronously"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._parse_pdf_sync, str(file_path), config
            )
        except Exception as e:
            raise ProcessingError(f"Failed to parse PDF: {str(e)}", e)

    async def parse_from_bytes_async(
        self, data: bytes, filename: str, config: ParserConfig
    ) -> ParsedDocument:
        """Parse PDF from bytes asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._parse_pdf_from_bytes_sync, data, filename, config
            )
        except Exception as e:
            raise ProcessingError(f"Failed to parse PDF from bytes: {str(e)}", e)

    def _parse_pdf_sync(self, file_path: str, config: ParserConfig) -> ParsedDocument:
        """Synchronous PDF parsing"""
        path = Path(file_path)
        document = asyncio.run(
            self._create_base_document(
                path, path.name, FileType.PDF, path.stat().st_size
            )
        )

        if HAS_PYMUPDF:
            return self._parse_with_pymupdf(file_path, document, config)
        elif HAS_PDFPLUMBER:
            return self._parse_with_pdfplumber(file_path, document, config)

    def _parse_pdf_from_bytes_sync(
        self, data: bytes, filename: str, config: ParserConfig
    ) -> ParsedDocument:
        """Synchronous PDF parsing from bytes"""
        document = asyncio.run(
            self._create_base_document(None, filename, FileType.PDF, len(data))
        )

        if HAS_PYMUPDF:
            return self._parse_bytes_with_pymupdf(data, document, config)
        elif HAS_PDFPLUMBER:
            return self._parse_bytes_with_pdfplumber(data, document, config)

    def _parse_with_pymupdf(
        self, file_path: str, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Parse PDF using PyMuPDF"""
        try:
            pdf_doc = fitz.open(file_path)
            return self._extract_with_pymupdf(pdf_doc, document, config)
        except Exception as e:
            raise ProcessingError(f"PyMuPDF parsing failed: {str(e)}", e)
        finally:
            if "pdf_doc" in locals():
                pdf_doc.close()

    def _parse_bytes_with_pymupdf(
        self, data: bytes, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Parse PDF bytes using PyMuPDF"""
        try:
            pdf_doc = fitz.open(stream=data, filetype="pdf")
            return self._extract_with_pymupdf(pdf_doc, document, config)
        except Exception as e:
            raise ProcessingError(f"PyMuPDF parsing failed: {str(e)}", e)
        finally:
            if "pdf_doc" in locals():
                pdf_doc.close()

    def _extract_with_pymupdf(
        self, pdf_doc: "fitz.Document", document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Extract content using PyMuPDF"""
        content_parts = []
        content_blocks = []
        tables = []
        images = []
        links = []

        # Update metadata
        document.metadata.page_count = pdf_doc.page_count
        if pdf_doc.metadata:
            meta = pdf_doc.metadata
            document.metadata.title = meta.get("title")
            document.metadata.author = meta.get("author")
            document.metadata.subject = meta.get("subject")
            document.metadata.custom_metadata = meta

        for page_num in range(pdf_doc.page_count):
            page = pdf_doc[page_num]

            # Extract text blocks
            if config.preserve_formatting:
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" in block:  # Text block
                        text_content = ""
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text_content += span["text"]
                            text_content += "\n"

                        if text_content.strip():
                            content_blocks.append(
                                ContentBlock(
                                    content=text_content.strip(),
                                    block_type="text",
                                    page_number=page_num + 1,
                                    position={
                                        "x": block["bbox"][0],
                                        "y": block["bbox"][1],
                                        "width": block["bbox"][2] - block["bbox"][0],
                                        "height": block["bbox"][3] - block["bbox"][1],
                                    },
                                )
                            )
                            content_parts.append(text_content.strip())
            else:
                # Simple text extraction
                text = page.get_text()
                if text.strip():
                    content_blocks.append(
                        ContentBlock(
                            content=text, block_type="text", page_number=page_num + 1
                        )
                    )
                    content_parts.append(text)

            # Extract tables if enabled
            if config.extract_tables:
                try:
                    page_tables = page.find_tables()
                    for table in page_tables:
                        table_data = table.extract()
                        tables.append(
                            {
                                "page": page_num + 1,
                                "data": table_data,
                                "bbox": table.bbox,
                            }
                        )
                except:
                    logging.warning(
                        f"Failed to extract tables from page {page_num + 1}"
                    )

            # Extract images if enabled
            if config.extract_images and HAS_PIL:
                try:
                    image_list = page.get_images()
                    for img_index, img in enumerate(image_list):
                        pix = fitz.Pixmap(pdf_doc, img[0])
                        if pix.n < 5:  # GRAY or RGB
                            img_data = pix.tobytes("png")
                            images.append(
                                {
                                    "page": page_num + 1,
                                    "index": img_index,
                                    "data": img_data,
                                    "width": pix.width,
                                    "height": pix.height,
                                }
                            )
                        pix = None
                except:
                    logging.warning(
                        f"Failed to extract images from page {page_num + 1}"
                    )

            # Extract links if enabled
            if config.extract_links:
                try:
                    page_links = page.get_links()
                    for link in page_links:
                        if link.get("uri"):
                            links.append(
                                {
                                    "page": page_num + 1,
                                    "url": link["uri"],
                                    "text": page.get_textbox(link["from"]).strip(),
                                }
                            )
                except:
                    logging.warning(f"Failed to extract links from page {page_num + 1}")

        # Combine content
        document.content = "\n\n".join(content_parts)
        document.content_blocks = content_blocks
        document.tables = tables
        document.images = images
        document.links = links

        # Update metadata
        document.metadata.word_count = len(document.content.split())
        document.metadata.character_count = len(document.content)

        return document

    def _parse_with_pdfplumber(
        self, file_path: str, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Parse PDF using pdfplumber (fallback)"""
        try:
            with pdfplumber.open(file_path) as pdf:
                return self._extract_with_pdfplumber(pdf, document, config)
        except Exception as e:
            raise ProcessingError(f"pdfplumber parsing failed: {str(e)}", e)

    def _parse_bytes_with_pdfplumber(
        self, data: bytes, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Parse PDF bytes using pdfplumber"""
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                return self._extract_with_pdfplumber(pdf, document, config)
        except Exception as e:
            raise ProcessingError(f"pdfplumber parsing failed: {str(e)}", e)

    def _extract_with_pdfplumber(
        self, pdf: "pdfplumber.PDF", document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Extract content using pdfplumber"""
        content_parts = []
        content_blocks = []
        tables = []

        # Update metadata
        document.metadata.page_count = len(pdf.pages)
        if pdf.metadata:
            document.metadata.title = pdf.metadata.get("Title")
            document.metadata.author = pdf.metadata.get("Author")
            document.metadata.subject = pdf.metadata.get("Subject")
            document.metadata.custom_metadata = pdf.metadata

        for page_num, page in enumerate(pdf.pages):
            # Extract text
            text = page.extract_text()
            if text and text.strip():
                content_blocks.append(
                    ContentBlock(
                        content=text, block_type="text", page_number=page_num + 1
                    )
                )
                content_parts.append(text)

            # Extract tables if enabled
            if config.extract_tables:
                try:
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:
                            tables.append({"page": page_num + 1, "data": table})
                except:
                    logging.warning(
                        f"Failed to extract tables from page {page_num + 1}"
                    )

        # Combine content
        document.content = "\n\n".join(content_parts)
        document.content_blocks = content_blocks
        document.tables = tables

        # Update metadata
        document.metadata.word_count = len(document.content.split())
        document.metadata.character_count = len(document.content)

        return document
