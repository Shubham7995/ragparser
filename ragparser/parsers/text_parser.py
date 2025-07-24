"""
Text parser for plain text files (TXT, MD, CSV, JSON)
"""

import asyncio
import json
import csv
import io
import logging
from typing import List, Dict, Any
from pathlib import Path

from .base import BaseParser
from ..core.models import ParsedDocument, ParserConfig, FileType, ContentBlock
from ..core.exceptions import ProcessingError


class TextParser(BaseParser):
    """Parser for text-based documents"""

    def __init__(self):
        super().__init__()
        self.supported_formats = [
            FileType.TXT,
            FileType.MD,
            FileType.CSV,
            FileType.JSON,
        ]

    async def parse_async(
        self, file_path: Path, config: ParserConfig
    ) -> ParsedDocument:
        """Parse text file asynchronously"""
        try:
            # Read file with encoding detection
            content = await self._read_file_with_encoding(file_path)
            return await self._process_text_content(
                content, file_path.name, file_path.stat().st_size, file_path, config
            )
        except Exception as e:
            raise ProcessingError(f"Failed to parse text file: {str(e)}", e)

    async def parse_from_bytes_async(
        self, data: bytes, filename: str, config: ParserConfig
    ) -> ParsedDocument:
        """Parse text from bytes asynchronously"""
        try:
            # Decode bytes with encoding detection
            content = await self._decode_bytes_with_encoding(data)
            return await self._process_text_content(
                content, filename, len(data), None, config
            )
        except Exception as e:
            raise ProcessingError(f"Failed to parse text from bytes: {str(e)}", e)

    async def _read_file_with_encoding(self, file_path: Path) -> str:
        """Read file with automatic encoding detection"""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # Fallback: read as binary and decode with errors='replace'
        with open(file_path, "rb") as f:
            content = f.read()
        return content.decode("utf-8", errors="replace")

    async def _decode_bytes_with_encoding(self, data: bytes) -> str:
        """Decode bytes with automatic encoding detection"""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue

        # Fallback
        return data.decode("utf-8", errors="replace")

    async def _process_text_content(
        self,
        content: str,
        filename: str,
        file_size: int,
        file_path: Path,
        config: ParserConfig,
    ) -> ParsedDocument:
        """Process text content based on file type"""

        # Determine file type
        file_type = self._detect_file_type(filename, content)

        # Create base document
        document = await self._create_base_document(
            file_path, filename, file_type, file_size
        )

        if file_type == FileType.JSON:
            return await self._process_json_content(content, document, config)
        elif file_type == FileType.CSV:
            return await self._process_csv_content(content, document, config)
        elif file_type == FileType.MD:
            return await self._process_markdown_content(content, document, config)
        else:
            return await self._process_plain_text_content(content, document, config)

    def _detect_file_type(self, filename: str, content: str) -> FileType:
        """Detect file type from filename and content"""
        filename_lower = filename.lower()

        if filename_lower.endswith(".json"):
            return FileType.JSON
        elif filename_lower.endswith(".csv"):
            return FileType.CSV
        elif filename_lower.endswith((".md", ".markdown")):
            return FileType.MD
        else:
            # Try to detect from content
            stripped_content = content.strip()
            if stripped_content.startswith(("{", "[")):
                try:
                    json.loads(stripped_content)
                    return FileType.JSON
                except:
                    pass

            # Check if it looks like CSV
            if "," in content and "\n" in content:
                try:
                    # Try to parse first few lines as CSV
                    lines = content.split("\n")[:5]
                    csv_content = "\n".join(lines)
                    list(csv.reader(io.StringIO(csv_content)))
                    return FileType.CSV
                except:
                    pass

        return FileType.TXT

    async def _process_json_content(
        self, content: str, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Process JSON content"""
        try:
            json_data = json.loads(content)

            # Convert JSON to readable text
            formatted_content = json.dumps(json_data, indent=2, ensure_ascii=False)
            document.content = formatted_content

            # Create content blocks for different parts
            if isinstance(json_data, dict):
                for key, value in json_data.items():
                    block_content = f"{key}: {json.dumps(value, indent=2)}"
                    document.content_blocks.append(
                        ContentBlock(content=block_content, block_type="json_field")
                    )
            elif isinstance(json_data, list):
                for i, item in enumerate(json_data):
                    block_content = f"Item {i+1}: {json.dumps(item, indent=2)}"
                    document.content_blocks.append(
                        ContentBlock(content=block_content, block_type="json_item")
                    )

            # Store original JSON data
            document.metadata.custom_metadata["json_data"] = json_data

        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse JSON: {str(e)}")
            # Fallback to plain text
            return await self._process_plain_text_content(content, document, config)

        # Update metadata
        document.metadata.word_count = len(document.content.split())
        document.metadata.character_count = len(document.content)

        return document

    async def _process_csv_content(
        self, content: str, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Process CSV content"""
        try:
            # Parse CSV
            csv_reader = csv.reader(io.StringIO(content))
            rows = list(csv_reader)

            if not rows:
                document.content = content
                return document

            headers = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []

            # Create readable text format
            content_parts = []

            if headers:
                content_parts.append(f"Headers: {', '.join(headers)}")
                content_parts.append("-" * 50)

            # Show sample of data
            max_preview_rows = config.custom_settings.get("csv_preview_rows", 10)
            for i, row in enumerate(data_rows[:max_preview_rows]):
                if headers and len(row) == len(headers):
                    row_dict = dict(zip(headers, row))
                    row_text = " | ".join([f"{k}: {v}" for k, v in row_dict.items()])
                else:
                    row_text = " | ".join(row)
                content_parts.append(f"Row {i+1}: {row_text}")

            if len(data_rows) > max_preview_rows:
                content_parts.append(
                    f"... and {len(data_rows) - max_preview_rows} more rows"
                )

            document.content = "\n".join(content_parts)

            # Create content blocks
            if headers:
                document.content_blocks.append(
                    ContentBlock(
                        content=f"CSV Headers: {', '.join(headers)}",
                        block_type="csv_header",
                    )
                )

            for i, row in enumerate(data_rows[:max_preview_rows]):
                document.content_blocks.append(
                    ContentBlock(content=" | ".join(row), block_type="csv_row")
                )

            # Store as table if enabled
            if config.extract_tables:
                document.tables.append(
                    {
                        "headers": headers,
                        "data": rows,
                        "row_count": len(rows),
                        "column_count": len(headers) if headers else 0,
                    }
                )

            # Store metadata
            document.metadata.custom_metadata.update(
                {
                    "csv_headers": headers,
                    "csv_row_count": len(data_rows),
                    "csv_column_count": len(headers) if headers else 0,
                }
            )

        except Exception as e:
            logging.warning(f"Failed to parse CSV: {str(e)}")
            # Fallback to plain text
            return await self._process_plain_text_content(content, document, config)

        # Update metadata
        document.metadata.word_count = len(document.content.split())
        document.metadata.character_count = len(document.content)

        return document

    async def _process_markdown_content(
        self, content: str, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Process Markdown content"""
        document.content = content

        # Parse markdown structure
        lines = content.split("\n")
        current_block = []
        current_block_type = "text"

        for line in lines:
            line_stripped = line.strip()

            if line_stripped.startswith("#"):
                # Save previous block
                if current_block:
                    block_content = "\n".join(current_block)
                    if block_content.strip():
                        document.content_blocks.append(
                            ContentBlock(
                                content=block_content, block_type=current_block_type
                            )
                        )
                    current_block = []

                # Start new header block
                level = len(line_stripped) - len(line_stripped.lstrip("#"))
                header_text = line_stripped.lstrip("#").strip()
                document.content_blocks.append(
                    ContentBlock(
                        content=header_text,
                        block_type=f"header_{level}",
                        formatting={"header_level": level},
                    )
                )
                current_block_type = "text"

            elif line_stripped.startswith("```"):
                # Code block
                if current_block:
                    block_content = "\n".join(current_block)
                    if block_content.strip():
                        document.content_blocks.append(
                            ContentBlock(
                                content=block_content, block_type=current_block_type
                            )
                        )
                    current_block = []

                if current_block_type != "code":
                    current_block_type = "code"
                else:
                    current_block_type = "text"

            elif line_stripped.startswith("|") and "|" in line_stripped[1:]:
                # Table row
                if current_block_type != "table":
                    if current_block:
                        block_content = "\n".join(current_block)
                        if block_content.strip():
                            document.content_blocks.append(
                                ContentBlock(
                                    content=block_content, block_type=current_block_type
                                )
                            )
                        current_block = []
                    current_block_type = "table"
                current_block.append(line)

            else:
                if current_block_type == "table":
                    # End of table
                    if current_block:
                        block_content = "\n".join(current_block)
                        if block_content.strip():
                            document.content_blocks.append(
                                ContentBlock(
                                    content=block_content, block_type=current_block_type
                                )
                            )
                        current_block = []
                    current_block_type = "text"

                current_block.append(line)

        # Save final block
        if current_block:
            block_content = "\n".join(current_block)
            if block_content.strip():
                document.content_blocks.append(
                    ContentBlock(content=block_content, block_type=current_block_type)
                )

        # Extract links if enabled
        if config.extract_links:
            import re

            # Markdown link pattern: [text](url)
            link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
            matches = re.findall(link_pattern, content)
            for text, url in matches:
                document.links.append({"text": text, "url": url})

        # Update metadata
        document.metadata.word_count = len(document.content.split())
        document.metadata.character_count = len(document.content)

        return document

    async def _process_plain_text_content(
        self, content: str, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """Process plain text content"""
        document.content = content

        # Split into paragraphs
        if config.merge_paragraphs:
            paragraphs = content.split("\n\n")
        else:
            paragraphs = content.split("\n")

        for para in paragraphs:
            para = para.strip()
            if para:
                document.content_blocks.append(
                    ContentBlock(content=para, block_type="text")
                )

        # Update metadata
        document.metadata.word_count = len(document.content.split())
        document.metadata.character_count = len(document.content)

        return document
