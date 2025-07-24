# RAG Parser

A comprehensive Python library for parsing documents into RAG-ready format. Supports PDF, DOCX, PPTX, XLSX, HTML, Markdown, and more with intelligent chunking strategies.

## 🚀 Features

- **Universal Document Parsing**: Support for PDF, DOCX, PPTX, XLSX, HTML, MD, CSV, JSON, and images
- **Intelligent Chunking**: Multiple strategies (Fixed, Semantic, Adaptive) optimized for RAG
- **Metadata Extraction**: Rich metadata including author, creation date, structure info
- **Content Structure Preservation**: Maintains headers, tables, images, and formatting context
- **Async Support**: Full async/await support for high-performance processing
- **RAG-Optimized Output**: Ready-to-embed chunks with proper citations and context
- **Framework Integration**: Built-in adapters for LangChain and LlamaIndex
- **Extensible Architecture**: Easy to add custom parsers and chunking strategies

## 📦 Installation

### Basic Installation
```bash
pip install ragparser
```

### With Specific Format Support
```bash
# PDF support
pip install ragparser[pdf]

# Office documents (DOCX, PPTX, XLSX)
pip install ragparser[office]

# HTML parsing
pip install ragparser[html]

# OCR for images
pip install ragparser[ocr]

# All formats
pip install ragparser[all]
```

### Development Installation
```bash
git clone https://github.com/shubham7995/ragparser.git
cd ragparser
pip install -e ".[dev]"
```

## 🎯 Quick Start

### Basic Usage

```python
from ragparser import RagParser
from ragparser.core.models import ParserConfig

# Initialize parser
parser = RagParser()

# Parse a document
result = parser.parse("document.pdf")

if result.success:
    document = result.document
    print(f"Extracted {len(document.content)} characters")
    print(f"Created {len(document.chunks)} chunks")
    print(f"Found {len(document.tables)} tables")
else:
    print(f"Error: {result.error}")
```

### Advanced Configuration

```python
from ragparser import RagParser, ParserConfig, ChunkingStrategy

# Custom configuration
config = ParserConfig(
    chunking_strategy=ChunkingStrategy.SEMANTIC,
    chunk_size=1000,
    chunk_overlap=200,
    extract_tables=True,
    extract_images=True,
    clean_text=True
)

parser = RagParser(config)
result = parser.parse("complex_document.pdf")
```

### Async Processing

```python
import asyncio
from ragparser import RagParser

async def process_documents():
    parser = RagParser()
    
    # Process single document
    result = await parser.parse_async("document.pdf")
    
    # Process multiple documents concurrently
    files = ["doc1.pdf", "doc2.docx", "doc3.pptx"]
    results = await parser.parse_multiple_async(files)
    
    for result in results:
        if result.success:
            print(f"Processed: {result.document.metadata.file_name}")

asyncio.run(process_documents())
```

### Processing from Bytes

```python
# Parse document from bytes (e.g., from web upload)
with open("document.pdf", "rb") as f:
    data = f.read()

result = parser.parse_from_bytes(data, "document.pdf")
```

## 📚 Supported Formats

| Format | Extensions | Features |
|--------|------------|----------|
| **PDF** | `.pdf` | Text, images, tables, metadata, OCR |
| **Word** | `.docx` | Text, formatting, tables, images, comments |
| **PowerPoint** | `.pptx` | Slides, speaker notes, images, tables |
| **Excel** | `.xlsx` | Sheets, formulas, charts, named ranges |
| **HTML** | `.html`, `.htm` | Structure, links, images, tables |
| **Markdown** | `.md`, `.markdown` | Headers, code blocks, tables, links |
| **Text** | `.txt` | Plain text with encoding detection |
| **CSV** | `.csv` | Structured data with header detection |
| **JSON** | `.json` | Structured data parsing |
| **Images** | `.png`, `.jpg`, `.gif`, etc. | OCR text extraction |

## 🔧 Chunking Strategies

### Fixed Chunking
```python
config = ParserConfig(
    chunking_strategy=ChunkingStrategy.FIXED,
    chunk_size=1000,
    chunk_overlap=200
)
```
- Splits text into fixed-size chunks
- Preserves sentence boundaries
- Configurable overlap for context

### Semantic Chunking
```python
config = ParserConfig(
    chunking_strategy=ChunkingStrategy.SEMANTIC,
    chunk_size=1000
)
```
- Groups content by semantic meaning
- Respects document structure (headers, paragraphs)
- Maintains topic coherence

### Adaptive Chunking
```python
config = ParserConfig(
    chunking_strategy=ChunkingStrategy.ADAPTIVE,
    chunk_size=1000
)
```
- Dynamically adjusts chunk size based on content
- Optimizes for embedding model context windows
- Balances size and semantic coherence

## 🔍 Content Extraction

### Text and Structure
```python
# Access extracted content
document = result.document

# Full text content
print(document.content)

# Structured content blocks
for block in document.content_blocks:
    print(f"{block.block_type}: {block.content}")

# Chunked content ready for RAG
for chunk in document.chunks:
    print(f"Chunk {chunk.chunk_id}: {len(chunk.content)} chars")
```

### Tables and Data
```python
# Extract tables
for table in document.tables:
    print(f"Table with {len(table['data'])} rows")
    headers = table.get('headers', [])
    print(f"Headers: {headers}")
```

### Metadata
```python
meta = document.metadata
print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
print(f"Pages: {meta.page_count}")
print(f"Words: {meta.word_count}")
```

## 🔗 Framework Integration

### LangChain Integration
```python
from ragparser.integrations.langchain_adapter import RagParserLoader

# Use as a LangChain document loader
loader = RagParserLoader("documents/")
documents = loader.load()

# With custom config
config = ParserConfig(chunking_strategy=ChunkingStrategy.SEMANTIC)
loader = RagParserLoader("documents/", config=config)
documents = loader.load()
```

### LlamaIndex Integration
```python
from ragparser.integrations.llamaindex_adapter import RagParserReader

# Use as a LlamaIndex reader
reader = RagParserReader()
documents = reader.load_data("document.pdf")
```

## ⚙️ Configuration Options

### Parser Configuration
```python
config = ParserConfig(
    # Chunking settings
    chunking_strategy=ChunkingStrategy.SEMANTIC,
    chunk_size=1000,
    chunk_overlap=200,
    
    # Content extraction
    extract_tables=True,
    extract_images=True,
    extract_metadata=True,
    extract_links=True,
    
    # Text processing
    clean_text=True,
    preserve_formatting=False,
    merge_paragraphs=True,
    
    # OCR settings
    enable_ocr=True,
    ocr_language="eng",
    ocr_confidence_threshold=0.7,
    
    # Performance
    max_file_size=100 * 1024 * 1024,  # 100MB
    timeout_seconds=300,
)
```

### Runtime Configuration Updates
```python
parser = RagParser()

# Update specific settings
parser.update_config(
    chunk_size=1500,
    extract_tables=False
)

# Add custom settings
parser.update_config(
    custom_ocr_model="my_model",
    special_processing=True
)
```

## 🚀 Performance Features

- **Async Processing**: Non-blocking document processing
- **Concurrent Parsing**: Process multiple documents simultaneously
- **Memory Efficient**: Streaming for large files
- **Caching**: Avoid reprocessing identical content
- **Lazy Loading**: Only load parsers for formats you use

## 📊 Monitoring and Quality

### Processing Statistics
```python
result = parser.parse("document.pdf")

stats = result.processing_stats
print(f"Processing time: {stats['processing_time']:.2f}s")
print(f"File size: {stats['file_size']} bytes")
print(f"Chunks created: {stats['chunk_count']}")
```

### Quality Metrics
```python
document = result.document

# Content quality indicators
print(f"Quality score: {document.quality_score}")
print(f"Extraction notes: {document.extraction_notes}")

# Chunk quality
for chunk in document.chunks:
    print(f"Chunk tokens: {chunk.token_count}")
    print(f"Embedding ready: {chunk.embedding_ready}")
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ragparser

# Run only fast tests
pytest -m "not slow"

# Run integration tests
pytest -m integration
```

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone repository
git clone https://github.com/shubham7995/ragparser.git
cd ragparser

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

### Adding New Parsers
```python
from ragparser.parsers.base import BaseParser
from ragparser.core.models import ParsedDocument, FileType

class MyCustomParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.supported_formats = [FileType.CUSTOM]
    
    async def parse_async(self, file_path, config):
        # Implement parsing logic
        return ParsedDocument(...)
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **GitHub**: https://github.com/shubham7995/ragparser
- **PyPI**: https://pypi.org/project/ragparser/
- **Documentation**: https://ragparser.readthedocs.io/
- **Issues**: https://github.com/shubham7995/ragparser/issues

## 🏷️ Keywords

`RAG`, `document parsing`, `PDF`, `DOCX`, `PPTX`, `XLSX`, `chunking`, `embedding`, `LangChain`, `LlamaIndex`, `async`, `OCR`, `metadata extraction`

---

Built with ❤️ for the RAG and LLM community