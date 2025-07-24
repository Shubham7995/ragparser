"""
Content cleaning and normalization processor
"""

import re
import logging
from typing import List, Dict, Any

from ..core.models import ParsedDocument, ParserConfig, ContentBlock


class ContentCleaner:
    """Clean and normalize document content"""

    async def clean_async(
        self, document: ParsedDocument, config: ParserConfig
    ) -> ParsedDocument:
        """
        Clean document content

        Args:
            document: Parsed document to clean
            config: Parser configuration

        Returns:
            Document with cleaned content
        """
        if not config.clean_text:
            return document

        try:
            # Clean main content
            document.content = await self._clean_text(document.content, config)

            # Clean content blocks
            cleaned_blocks = []
            for block in document.content_blocks:
                cleaned_block = await self._clean_content_block(block, config)
                if cleaned_block.content.strip():  # Only keep non-empty blocks
                    cleaned_blocks.append(cleaned_block)

            document.content_blocks = cleaned_blocks

            # Clean tables
            if document.tables:
                document.tables = await self._clean_tables(document.tables, config)

            # Update metadata
            document.metadata.word_count = len(document.content.split())
            document.metadata.character_count = len(document.content)

        except Exception as e:
            logging.warning(f"Error cleaning content: {str(e)}")

        return document

    async def _clean_text(self, text: str, config: ParserConfig) -> str:
        """Clean and normalize text content"""
        if not text:
            return text

        # Basic cleaning
        cleaned = text

        # Remove excessive whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(
            r"\n\s*\n\s*\n+", "\n\n", cleaned
        )  # Max 2 consecutive newlines

        # Remove common artifacts
        cleaned = await self._remove_artifacts(cleaned, config)

        # Normalize unicode
        cleaned = await self._normalize_unicode(cleaned)

        # Fix common formatting issues
        cleaned = await self._fix_formatting(cleaned, config)

        # Remove empty lines and trim
        lines = [line.rstrip() for line in cleaned.split("\n")]
        cleaned = "\n".join(lines).strip()

        return cleaned

    async def _remove_artifacts(self, text: str, config: ParserConfig) -> str:
        """Remove common document artifacts"""

        # Remove page numbers at end of lines
        text = re.sub(r"\s+\d+\s*$", "", text, flags=re.MULTILINE)

        # Remove headers/footers patterns
        header_footer_patterns = [
            r"^Page \d+ of \d+.*$",
            r"^\d+\s*$",  # Standalone page numbers
            r"^-\s*\d+\s*-$",  # Page numbers with dashes
            r"^\s*\|\s*Page\s+\d+\s*\|\s*$",  # Boxed page numbers
        ]

        for pattern in header_footer_patterns:
            text = re.sub(pattern, "", text, flags=re.MULTILINE)

        # Remove excessive dots/dashes (table of contents artifacts)
        text = re.sub(r"\.{4,}", "...", text)
        text = re.sub(r"-{4,}", "---", text)
        text = re.sub(r"_{4,}", "___", text)

        # Remove form field artifacts
        text = re.sub(r"\[\s*\]", "", text)  # Empty checkboxes
        text = re.sub(r"_{3,}", "", text)  # Underlines for form fields

        # Remove OCR artifacts
        ocr_artifacts = [
            r"[|Il1]{3,}",  # Vertical line artifacts
            r"[^\w\s]{5,}",  # Long sequences of special chars
        ]

        for pattern in ocr_artifacts:
            text = re.sub(pattern, "", text)

        return text

    async def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters"""
        import unicodedata

        # Normalize unicode
        text = unicodedata.normalize("NFKC", text)

        # Replace common unicode variants
        replacements = {
            """: "'",  # Smart quote
            """: "'",  # Smart quote
            '"': '"',  # Smart quote
            '"': '"',  # Smart quote
            "–": "-",  # En dash
            "—": "--",  # Em dash
            "…": "...",  # Ellipsis
            "®": "(R)",  # Registered
            "©": "(C)",  # Copyright
            "™": "(TM)",  # Trademark
            " ": " ",  # Non-breaking space
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    async def _fix_formatting(self, text: str, config: ParserConfig) -> str:
        """Fix common formatting issues"""

        # Fix spacing around punctuation
        text = re.sub(r"\s+([,.!?;:])", r"\1", text)  # Remove space before punctuation
        text = re.sub(
            r"([,.!?;:])\s+", r"\1 ", text
        )  # Ensure one space after punctuation

        # Fix quotation marks
        text = re.sub(r'\s+"', ' "', text)  # Space before opening quote
        text = re.sub(r'"\s+', '" ', text)  # Space after closing quote

        # Fix common abbreviations
        abbreviations = ["Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Inc.", "Ltd.", "Corp."]
        for abbr in abbreviations:
            text = re.sub(f"{abbr}\\s+", f"{abbr} ", text)

        # Fix sentence spacing
        text = re.sub(r"([.!?])\s*([A-Z])", r"\1 \2", text)

        # Fix hyphenated words broken across lines
        text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

        return text

    async def _clean_content_block(
        self, block: ContentBlock, config: ParserConfig
    ) -> ContentBlock:
        """Clean individual content block"""
        cleaned_content = await self._clean_text(block.content, config)

        return ContentBlock(
            content=cleaned_content,
            block_type=block.block_type,
            page_number=block.page_number,
            position=block.position,
            formatting=block.formatting,
            confidence=block.confidence,
        )

    async def _clean_tables(
        self, tables: List[Dict[str, Any]], config: ParserConfig
    ) -> List[Dict[str, Any]]:
        """Clean table data"""
        cleaned_tables = []

        for table in tables:
            cleaned_table = table.copy()

            # Clean table data
            if "data" in table:
                cleaned_data = []
                for row in table["data"]:
                    cleaned_row = []
                    for cell in row:
                        if isinstance(cell, str):
                            cleaned_cell = await self._clean_text(cell, config)
                            cleaned_row.append(cleaned_cell)
                        else:
                            cleaned_row.append(cell)

                    # Only keep non-empty rows
                    if any(str(cell).strip() for cell in cleaned_row):
                        cleaned_data.append(cleaned_row)

                cleaned_table["data"] = cleaned_data

            # Clean headers
            if "headers" in table:
                cleaned_headers = []
                for header in table["headers"]:
                    if isinstance(header, str):
                        cleaned_header = await self._clean_text(header, config)
                        cleaned_headers.append(cleaned_header)
                    else:
                        cleaned_headers.append(header)

                cleaned_table["headers"] = cleaned_headers

            cleaned_tables.append(cleaned_table)

        return cleaned_tables

    def _is_likely_noise(self, text: str) -> bool:
        """Determine if text is likely noise/artifacts"""
        if not text or len(text.strip()) < 3:
            return True

        # Check for excessive special characters
        special_char_ratio = len(
            [c for c in text if not c.isalnum() and not c.isspace()]
        ) / len(text)
        if special_char_ratio > 0.5:
            return True

        # Check for repetitive patterns
        if len(set(text.replace(" ", ""))) < 3:  # Very few unique characters
            return True

        # Check for common noise patterns
        noise_patterns = [
            r"^[|Il1\s]+$",  # Only vertical line artifacts
            r"^[.\-_\s]+$",  # Only dots, dashes, underscores
            r"^[\d\s]+$",  # Only numbers and spaces (except if reasonable page numbers)
        ]

        for pattern in noise_patterns:
            if re.match(pattern, text):
                return True

        return False
