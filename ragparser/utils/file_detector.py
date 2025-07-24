"""
File type detection utilities
"""

import mimetypes
from pathlib import Path
from typing import Optional

from ..core.models import FileType


class FileDetector:
    """Detect file types from paths, extensions, and content"""

    def __init__(self):
        self.extension_mapping = {
            ".pdf": FileType.PDF,
            ".docx": FileType.DOCX,
            ".pptx": FileType.PPTX,
            ".xlsx": FileType.XLSX,
            ".txt": FileType.TXT,
            ".md": FileType.MD,
            ".markdown": FileType.MD,
            ".html": FileType.HTML,
            ".htm": FileType.HTML,
            ".csv": FileType.CSV,
            ".json": FileType.JSON,
            ".png": FileType.IMAGE,
            ".jpg": FileType.IMAGE,
            ".jpeg": FileType.IMAGE,
            ".gif": FileType.IMAGE,
            ".bmp": FileType.IMAGE,
            ".tiff": FileType.IMAGE,
            ".webp": FileType.IMAGE,
        }

        self.mime_mapping = {
            "application/pdf": FileType.PDF,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PPTX,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
            "text/plain": FileType.TXT,
            "text/markdown": FileType.MD,
            "text/html": FileType.HTML,
            "text/csv": FileType.CSV,
            "application/json": FileType.JSON,
            "image/png": FileType.IMAGE,
            "image/jpeg": FileType.IMAGE,
            "image/gif": FileType.IMAGE,
            "image/bmp": FileType.IMAGE,
            "image/tiff": FileType.IMAGE,
            "image/webp": FileType.IMAGE,
        }

    def detect_type(self, file_path: Path) -> FileType:
        """
        Detect file type from file path

        Args:
            file_path: Path to the file

        Returns:
            Detected file type
        """
        # First try extension
        extension = file_path.suffix.lower()
        if extension in self.extension_mapping:
            return self.extension_mapping[extension]

        # Try MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type in self.mime_mapping:
            return self.mime_mapping[mime_type]

        # Try content-based detection if file exists
        if file_path.exists():
            return self.detect_from_content(file_path)

        # Default fallback
        return FileType.TXT

    def detect_type_from_bytes(self, data: bytes, filename: str) -> FileType:
        """
        Detect file type from bytes and filename

        Args:
            data: File data as bytes
            filename: Original filename

        Returns:
            Detected file type
        """
        # First try filename extension
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        if extension in self.extension_mapping:
            return self.extension_mapping[extension]

        # Try magic number detection
        return self.detect_from_magic_numbers(data, filename)

    def detect_from_content(self, file_path: Path) -> FileType:
        """
        Detect file type from file content

        Args:
            file_path: Path to the file

        Returns:
            Detected file type
        """
        try:
            with open(file_path, "rb") as f:
                header = f.read(1024)  # Read first 1KB

            return self.detect_from_magic_numbers(header, file_path.name)
        except:
            return FileType.TXT

    def detect_from_magic_numbers(self, data: bytes, filename: str = "") -> FileType:
        """
        Detect file type from magic numbers (file signatures)

        Args:
            data: File data bytes
            filename: Optional filename for additional context

        Returns:
            Detected file type
        """
        if not data:
            return FileType.TXT

        # PDF
        if data.startswith(b"%PDF"):
            return FileType.PDF

        # Office documents (ZIP-based)
        if data.startswith(b"PK\x03\x04"):
            # Could be DOCX, PPTX, XLSX - check filename
            filename_lower = filename.lower()
            if filename_lower.endswith(".docx"):
                return FileType.DOCX
            elif filename_lower.endswith(".pptx"):
                return FileType.PPTX
            elif filename_lower.endswith(".xlsx"):
                return FileType.XLSX
            else:
                # Try to detect from ZIP content (more complex)
                return self._detect_office_from_zip(data)

        # Images
        if data.startswith(b"\x89PNG"):
            return FileType.IMAGE
        if data.startswith(b"\xff\xd8\xff"):
            return FileType.IMAGE
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return FileType.IMAGE
        if data.startswith(b"BM"):
            return FileType.IMAGE
        if data.startswith(b"RIFF") and b"WEBP" in data[:12]:
            return FileType.IMAGE

        # HTML
        html_indicators = [b"<!DOCTYPE html", b"<html", b"<HTML", b"<head", b"<HEAD"]
        if any(indicator in data[:200] for indicator in html_indicators):
            return FileType.HTML

        # JSON
        stripped_data = data.strip()
        if stripped_data.startswith((b"{", b"[")):
            try:
                import json

                json.loads(stripped_data.decode("utf-8"))
                return FileType.JSON
            except:
                pass

        # CSV (basic heuristic)
        try:
            text_data = data.decode("utf-8")[:1000]
            if "," in text_data and "\n" in text_data:
                # Count commas vs other separators
                comma_count = text_data.count(",")
                tab_count = text_data.count("\t")
                semicolon_count = text_data.count(";")

                if comma_count > max(tab_count, semicolon_count):
                    return FileType.CSV
        except:
            pass

        # Markdown (check for markdown syntax)
        try:
            text_data = data.decode("utf-8")[:1000]
            markdown_indicators = ["#", "*", "_", "`", "[", "]", "(", ")"]
            if any(indicator in text_data for indicator in markdown_indicators):
                # Simple heuristic: if it has markdown-like syntax
                if text_data.count("#") > 0 or text_data.count("*") > 2:
                    return FileType.MD
        except:
            pass

        # Default to text
        return FileType.TXT

    def _detect_office_from_zip(self, data: bytes) -> FileType:
        """
        Try to detect specific Office document type from ZIP content
        This is a simplified version - full detection would require ZIP parsing
        """
        try:
            # Look for specific strings that might indicate document type
            if b"word/" in data[:2048]:
                return FileType.DOCX
            elif b"ppt/" in data[:2048]:
                return FileType.PPTX
            elif b"xl/" in data[:2048]:
                return FileType.XLSX
        except:
            pass

        # Default to DOCX if can't determine
        return FileType.DOCX

    def is_supported(self, file_type: FileType) -> bool:
        """Check if file type is supported"""
        return file_type in FileType

    def get_supported_extensions(self) -> list[str]:
        """Get list of supported file extensions"""
        return list(self.extension_mapping.keys())
