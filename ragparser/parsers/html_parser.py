"""
HTML parser implementation using BeautifulSoup
"""

import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path
import re

try:
    from bs4 import BeautifulSoup, NavigableString

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from .base import BaseParser
from ..core.models import ParsedDocument, ParserConfig, FileType, ContentBlock
from ..core.exceptions import ProcessingError


class HTMLParser(BaseParser):
    """Parser for HTML documents"""

    def __init__(self):
        super().__init__()
        self.supported_formats = [FileType.HTML]

        if not HAS_BS4:
            raise ImportError(
                "HTML parsing requires BeautifulSoup4. Install with: pip install beautifulsoup4"
            )

    async def parse_async(
        self, file_path: Path, config: ParserConfig
    ) -> ParsedDocument:
        """Parse HTML file asynchronously"""
        try:
            # Read file with encoding detection
            content = await self._read_html_file(file_path)
            return await self._process_html_content(
                content, file_path.name, file_path.stat().st_size, file_path, config
            )
        except Exception as e:
            raise ProcessingError(f"Failed to parse HTML: {str(e)}", e)

    async def parse_from_bytes_async(
        self, data: bytes, filename: str, config: ParserConfig
    ) -> ParsedDocument:
        """Parse HTML from bytes asynchronously"""
        try:
            # Decode HTML with encoding detection
            content = await self._decode_html_bytes(data)
            return await self._process_html_content(
                content, filename, len(data), None, config
            )
        except Exception as e:
            raise ProcessingError(f"Failed to parse HTML from bytes: {str(e)}", e)

    async def _read_html_file(self, file_path: Path) -> str:
        """Read HTML file with encoding detection"""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # Fallback
        with open(file_path, "rb") as f:
            content = f.read()
        return content.decode("utf-8", errors="replace")

    async def _decode_html_bytes(self, data: bytes) -> str:
        """Decode HTML bytes with encoding detection"""
        # Try to detect encoding from HTML meta tags
        try:
            # Look for charset in first 1024 bytes
            header = data[:1024].decode("ascii", errors="ignore").lower()
            charset_match = re.search(r'charset["\s]*=["\s]*([^"\'>\s]+)', header)
            if charset_match:
                encoding = charset_match.group(1)
                try:
                    return data.decode(encoding)
                except:
                    pass
        except:
            pass

        # Fallback encodings
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]

        for encoding in encodings:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue

        return data.decode("utf-8", errors="replace")

    async def _process_html_content(
        self,
        content: str,
        filename: str,
        file_size: int,
        file_path: Path,
        config: ParserConfig,
    ) -> ParsedDocument:
        """Process HTML content"""

        # Create base document
        document = await self._create_base_document(
            file_path, filename, FileType.HTML, file_size
        )

        try:
            soup = BeautifulSoup(content, "html.parser")

            # Extract metadata from HTML head
            await self._extract_html_metadata(soup, document)

            # Extract content blocks
            content_parts = []
            document.content_blocks = []

            # Process body content
            body = soup.find("body")
            if body:
                await self._extract_content_blocks(
                    body, document, config, content_parts
                )
            else:
                # No body tag, process entire document
                await self._extract_content_blocks(
                    soup, document, config, content_parts
                )

            # Extract tables if enabled
            if config.extract_tables:
                await self._extract_tables(soup, document)

            # Extract links if enabled
            if config.extract_links:
                await self._extract_links(soup, document)

            # Extract images if enabled
            if config.extract_images:
                await self._extract_images(soup, document)

            # Combine content
            document.content = "\n\n".join(content_parts)

            # Update metadata
            document.metadata.word_count = len(document.content.split())
            document.metadata.character_count = len(document.content)

        except Exception as e:
            logging.warning(f"Failed to parse HTML with BeautifulSoup: {str(e)}")
            # Fallback: extract text using regex
            document.content = self._extract_text_fallback(content)
            document.content_blocks.append(
                ContentBlock(content=document.content, block_type="text")
            )

        return document

    async def _extract_html_metadata(
        self, soup: BeautifulSoup, document: ParsedDocument
    ):
        """Extract metadata from HTML head"""
        head = soup.find("head")
        if not head:
            return

        # Title
        title_tag = head.find("title")
        if title_tag:
            document.metadata.title = title_tag.get_text().strip()

        # Meta tags
        meta_tags = head.find_all("meta")
        metadata = {}

        for meta in meta_tags:
            if meta.get("name"):
                name = meta.get("name").lower()
                content = meta.get("content", "")

                if name == "author":
                    document.metadata.author = content
                elif name == "description":
                    document.metadata.subject = content
                elif name in ["keywords", "description", "author", "robots"]:
                    metadata[name] = content

            elif meta.get("property"):
                # Open Graph tags
                prop = meta.get("property")
                content = meta.get("content", "")
                metadata[prop] = content

        document.metadata.custom_metadata = metadata

    async def _extract_content_blocks(
        self,
        element,
        document: ParsedDocument,
        config: ParserConfig,
        content_parts: List[str],
    ):
        """Extract content blocks from HTML elements"""

        for child in element.children:
            if isinstance(child, NavigableString):
                text = child.strip()
                if text:
                    content_parts.append(text)
                    document.content_blocks.append(
                        ContentBlock(content=text, block_type="text")
                    )
                continue

            if not hasattr(child, "name"):
                continue

            tag_name = child.name.lower()
            text_content = child.get_text().strip()

            if not text_content:
                continue

            # Determine block type based on HTML tag
            block_type = self._get_block_type(tag_name)

            # Skip script and style tags
            if tag_name in ["script", "style", "meta", "link"]:
                continue

            # Handle specific tags
            if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                content_parts.append(text_content)
                document.content_blocks.append(
                    ContentBlock(
                        content=text_content,
                        block_type=f"header_{tag_name[1]}",
                        formatting={"tag": tag_name, "header_level": int(tag_name[1])},
                    )
                )

            elif tag_name in ["p", "div", "article", "section"]:
                if len(text_content) > 20:  # Avoid very short divs
                    content_parts.append(text_content)
                    document.content_blocks.append(
                        ContentBlock(
                            content=text_content,
                            block_type=block_type,
                            formatting={"tag": tag_name},
                        )
                    )

            elif tag_name in ["blockquote"]:
                content_parts.append(f"Quote: {text_content}")
                document.content_blocks.append(
                    ContentBlock(
                        content=text_content,
                        block_type="quote",
                        formatting={"tag": tag_name},
                    )
                )

            elif tag_name in ["pre", "code"]:
                content_parts.append(f"Code: {text_content}")
                document.content_blocks.append(
                    ContentBlock(
                        content=text_content,
                        block_type="code",
                        formatting={"tag": tag_name},
                    )
                )

            elif tag_name in ["li"]:
                content_parts.append(f"• {text_content}")
                document.content_blocks.append(
                    ContentBlock(
                        content=text_content,
                        block_type="list_item",
                        formatting={"tag": tag_name},
                    )
                )

            else:
                # Recursively process child elements
                await self._extract_content_blocks(
                    child, document, config, content_parts
                )

    def _get_block_type(self, tag_name: str) -> str:
        """Map HTML tag to block type"""
        mapping = {
            "h1": "header_1",
            "h2": "header_2",
            "h3": "header_3",
            "h4": "header_4",
            "h5": "header_5",
            "h6": "header_6",
            "p": "text",
            "div": "text",
            "span": "text",
            "article": "text",
            "section": "text",
            "blockquote": "quote",
            "pre": "code",
            "code": "code",
            "li": "list_item",
            "ul": "list",
            "ol": "list",
            "table": "table",
            "tr": "table_row",
            "td": "table_cell",
            "th": "table_header",
        }
        return mapping.get(tag_name, "text")

    async def _extract_tables(self, soup: BeautifulSoup, document: ParsedDocument):
        """Extract tables from HTML"""
        tables = soup.find_all("table")

        for table_idx, table in enumerate(tables):
            try:
                table_data = []
                headers = []

                # Extract headers
                header_row = table.find("tr")
                if header_row:
                    header_cells = header_row.find_all(["th", "td"])
                    headers = [cell.get_text().strip() for cell in header_cells]

                # Extract rows
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    row_data = [cell.get_text().strip() for cell in cells]
                    if row_data:
                        table_data.append(row_data)

                if table_data:
                    document.tables.append(
                        {"index": table_idx, "headers": headers, "data": table_data}
                    )

            except Exception as e:
                logging.warning(f"Failed to extract table {table_idx}: {str(e)}")

    async def _extract_links(self, soup: BeautifulSoup, document: ParsedDocument):
        """Extract links from HTML"""
        links = soup.find_all("a", href=True)

        for link in links:
            href = link.get("href")
            text = link.get_text().strip()

            if href and text:
                document.links.append({"text": text, "url": href})

    async def _extract_images(self, soup: BeautifulSoup, document: ParsedDocument):
        """Extract image information from HTML"""
        images = soup.find_all("img")

        for img_idx, img in enumerate(images):
            img_data = {
                "index": img_idx,
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
                "title": img.get("title", ""),
            }

            if img_data["src"]:
                document.images.append(img_data)

    def _extract_text_fallback(self, html_content: str) -> str:
        """Fallback text extraction using regex"""
        # Remove script and style tags
        html_content = re.sub(
            r"<script[^>]*>.*?</script>",
            "",
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html_content = re.sub(
            r"<style[^>]*>.*?</style>",
            "",
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html_content)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()
