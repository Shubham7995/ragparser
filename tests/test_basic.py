"""
Basic tests for RAG Parser
"""

import pytest
import tempfile
import os
from pathlib import Path

from ragparser import RagParser, ParserConfig, ChunkingStrategy, FileType
from ragparser.core.exceptions import UnsupportedFormatError, FileSizeError


class TestBasicParsing:
    """Test basic parsing functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.parser = RagParser()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_file(self, content: str, filename: str) -> Path:
        """Create a test file with given content"""
        file_path = Path(self.temp_dir) / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_text_file_parsing(self):
        """Test parsing a simple text file"""
        content = "This is a test document.\n\nIt has multiple paragraphs.\n\nThis is the third paragraph."
        file_path = self.create_test_file(content, "test.txt")

        result = self.parser.parse(file_path)

        assert result.success
        assert result.document is not None
        assert result.document.content == content
        assert result.document.metadata.file_type == FileType.TXT
        assert result.document.metadata.word_count > 0
        assert len(result.document.chunks) > 0

    def test_markdown_file_parsing(self):
        """Test parsing a markdown file"""
        content = """# Main Title
        
This is a paragraph under the main title.

## Subtitle

This is content under subtitle.

- List item 1
- List item 2

```python
def hello():
    print("Hello, World!")
```
"""
        file_path = self.create_test_file(content, "test.md")

        result = self.parser.parse(file_path)

        assert result.success
        assert result.document.metadata.file_type == FileType.MD

        # Check that headers were detected
        header_blocks = [
            b
            for b in result.document.content_blocks
            if b.block_type.startswith("header")
        ]
        assert len(header_blocks) >= 2  # Main title and subtitle

    def test_csv_file_parsing(self):
        """Test parsing a CSV file"""
        content = """Name,Age,City
John,25,New York
Jane,30,Los Angeles
Bob,35,Chicago"""

        file_path = self.create_test_file(content, "test.csv")

        result = self.parser.parse(file_path)

        assert result.success
        assert result.document.metadata.file_type == FileType.CSV
        assert len(result.document.tables) == 1

        table = result.document.tables[0]
        assert "headers" in table
        assert table["headers"] == ["Name", "Age", "City"]

    def test_json_file_parsing(self):
        """Test parsing a JSON file"""
        content = """{
    "name": "Test Document",
    "data": [
        {"id": 1, "value": "first"},
        {"id": 2, "value": "second"}
    ],
    "metadata": {
        "version": "1.0",
        "created": "2024-01-01"
    }
}"""

        file_path = self.create_test_file(content, "test.json")

        result = self.parser.parse(file_path)

        assert result.success
        assert result.document.metadata.file_type == FileType.JSON
        assert "json_data" in result.document.metadata.custom_metadata

    def test_html_file_parsing(self):
        """Test parsing an HTML file"""
        content = """<!DOCTYPE html>
<html>
<head>
    <title>Test Document</title>
</head>
<body>
    <h1>Main Heading</h1>
    <p>This is a paragraph with <strong>bold text</strong>.</p>
    <h2>Subheading</h2>
    <p>Another paragraph with <a href="https://example.com">a link</a>.</p>
    <ul>
        <li>List item 1</li>
        <li>List item 2</li>
    </ul>
</body>
</html>"""

        file_path = self.create_test_file(content, "test.html")

        result = self.parser.parse(file_path)

        assert result.success
        assert result.document.metadata.file_type == FileType.HTML
        assert result.document.metadata.title == "Test Document"

        # Check for extracted links
        if result.document.links:
            assert any(
                "example.com" in link.get("url", "") for link in result.document.links
            )


class TestConfiguration:
    """Test parser configuration"""

    def test_custom_config(self):
        """Test parsing with custom configuration"""
        config = ParserConfig(
            chunking_strategy=ChunkingStrategy.FIXED,
            chunk_size=100,
            chunk_overlap=20,
            extract_tables=False,
            clean_text=True,
        )

        parser = RagParser(config)

        # Test with simple text
        content = "This is a test. " * 20  # Long enough to create multiple chunks
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()

            result = parser.parse(Path(f.name))

            assert result.success
            assert len(result.document.chunks) > 1  # Should create multiple chunks

            # Check chunk sizes are approximately correct
            for chunk in result.document.chunks:
                assert len(chunk.content) <= config.chunk_size + 50  # Some tolerance

            os.unlink(f.name)

    def test_semantic_chunking(self):
        """Test semantic chunking strategy"""
        config = ParserConfig(
            chunking_strategy=ChunkingStrategy.SEMANTIC, chunk_size=200
        )

        parser = RagParser(config)

        content = """# Introduction
This is the introduction section.

# Methods
This section describes the methods used.

## Data Collection
Details about data collection.

## Analysis
Details about analysis.

# Results
This section presents the results.

# Conclusion
Final thoughts and conclusions."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            result = parser.parse(Path(f.name))

            assert result.success
            assert len(result.document.chunks) > 0

            # Check that chunks have semantic metadata
            for chunk in result.document.chunks:
                assert "chunk_method" in chunk.metadata
                assert chunk.metadata["chunk_method"] in [
                    "semantic",
                    "semantic_split",
                    "semantic_fallback",
                ]

            os.unlink(f.name)


class TestErrorHandling:
    """Test error handling"""

    def test_nonexistent_file(self):
        """Test handling of non-existent file"""
        parser = RagParser()
        result = parser.parse("nonexistent_file.txt")

        assert not result.success
        assert result.error is not None
        assert (
            "not found" in result.error.lower()
            or "no such file" in result.error.lower()
        )

    def test_empty_file(self):
        """Test handling of empty file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")  # Empty file
            f.flush()

            parser = RagParser()
            result = parser.parse(Path(f.name))

            # Should handle empty file gracefully
            assert not result.success or (
                result.success and result.document.content == ""
            )

            os.unlink(f.name)

    def test_file_size_limit(self):
        """Test file size limit enforcement"""
        config = ParserConfig(max_file_size=100)  # Very small limit
        parser = RagParser(config)

        # Create file larger than limit
        large_content = "x" * 200  # 200 bytes

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(large_content)
            f.flush()

            result = parser.parse(Path(f.name))

            assert not result.success
            assert "size" in result.error.lower()

            os.unlink(f.name)


class TestAsyncParsing:
    """Test asynchronous parsing"""

    @pytest.mark.asyncio
    async def test_async_single_file(self):
        """Test async parsing of single file"""
        parser = RagParser()

        content = "This is an async test document."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()

            result = await parser.parse_async(Path(f.name))

            assert result.success
            assert result.document.content == content

            os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_async_multiple_files(self):
        """Test async parsing of multiple files"""
        parser = RagParser()

        files = []
        for i in range(3):
            content = f"This is test document {i+1}."
            f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
            f.write(content)
            f.flush()
            f.close()
            files.append(Path(f.name))

        try:
            results = await parser.parse_multiple_async(files)

            assert len(results) == 3

            for i, result in enumerate(results):
                assert result.success
                assert f"document {i+1}" in result.document.content

        finally:
            for f in files:
                os.unlink(f)

    @pytest.mark.asyncio
    async def test_parse_from_bytes(self):
        """Test parsing from bytes"""
        parser = RagParser()

        content = "This is a test document from bytes."
        data = content.encode("utf-8")

        result = await parser.parse_from_bytes_async(data, "test.txt")

        assert result.success
        assert result.document.content == content
        assert result.document.metadata.file_name == "test.txt"


class TestUtilities:
    """Test utility functions"""

    def test_supported_formats(self):
        """Test getting supported formats"""
        parser = RagParser()
        formats = parser.get_supported_formats()

        assert isinstance(formats, list)
        assert len(formats) > 0
        assert "txt" in formats
        assert "md" in formats
        assert "html" in formats

    def test_config_updates(self):
        """Test configuration updates"""
        parser = RagParser()

        # Initial config
        assert parser.config.chunk_size == 1000  # Default

        # Update config
        parser.update_config(chunk_size=1500, extract_tables=False)

        assert parser.config.chunk_size == 1500
        assert parser.config.extract_tables == False

        # Update with custom setting
        parser.update_config(custom_setting="test_value")

        assert parser.config.custom_settings["custom_setting"] == "test_value"
