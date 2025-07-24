"""
Basic usage examples for RAG Parser
"""

import asyncio
from pathlib import Path
from ragparser import RagParser, ParserConfig, ChunkingStrategy


def basic_example():
    """Basic document parsing example"""
    print("=== Basic Document Parsing ===")

    # Initialize parser with default configuration
    parser = RagParser()

    # Parse a document (replace with your file path)
    result = parser.parse("sample_document.pdf")

    if result.success:
        document = result.document
        print(f"✅ Successfully parsed: {document.metadata.file_name}")
        print(f"📄 Content length: {len(document.content)} characters")
        print(f"📊 Word count: {document.metadata.word_count}")
        print(f"🧩 Chunks created: {len(document.chunks)}")
        print(f"📋 Tables found: {len(document.tables)}")
        print(f"🖼️ Images found: {len(document.images)}")
        print(f"🔗 Links found: {len(document.links)}")
        print(f"⏱️ Processing time: {document.processing_time:.2f}s")

        # Display first chunk
        if document.chunks:
            first_chunk = document.chunks[0]
            print(f"\n📝 First chunk preview:")
            print(f"ID: {first_chunk.chunk_id}")
            print(f"Content: {first_chunk.content[:200]}...")
            print(f"Tokens: {first_chunk.token_count}")

    else:
        print(f"❌ Error parsing document: {result.error}")


def advanced_configuration_example():
    """Example with custom configuration"""
    print("\n=== Advanced Configuration ===")

    # Create custom configuration
    config = ParserConfig(
        chunking_strategy=ChunkingStrategy.SEMANTIC,
        chunk_size=1500,
        chunk_overlap=300,
        extract_tables=True,
        extract_images=True,
        extract_metadata=True,
        extract_links=True,
        clean_text=True,
        preserve_formatting=False,
        merge_paragraphs=True,
        enable_ocr=True,
        ocr_language="eng",
    )

    # Initialize parser with custom config
    parser = RagParser(config)

    # Parse document
    result = parser.parse("sample_document.pdf")

    if result.success:
        document = result.document
        print(f"✅ Parsed with semantic chunking: {document.metadata.file_name}")
        print(f"🧩 Semantic chunks: {len(document.chunks)}")

        # Show chunk metadata
        for i, chunk in enumerate(document.chunks[:3]):  # First 3 chunks
            print(f"\nChunk {i+1}:")
            print(f"  Method: {chunk.metadata.get('chunk_method', 'unknown')}")
            print(f"  Type: {chunk.metadata.get('semantic_type', 'unknown')}")
            print(f"  Length: {len(chunk.content)} chars")

    else:
        print(f"❌ Error: {result.error}")


async def async_processing_example():
    """Asynchronous processing example"""
    print("\n=== Async Processing ===")

    parser = RagParser()

    # Single async parse
    result = await parser.parse_async("sample_document.pdf")
    if result.success:
        print(f"✅ Async parse completed: {result.document.metadata.file_name}")

    # Multiple documents concurrently
    file_paths = ["document1.pdf", "document2.docx", "document3.pptx"]

    # Filter to existing files for demo
    existing_files = [path for path in file_paths if Path(path).exists()]

    if existing_files:
        print(f"📁 Processing {len(existing_files)} documents concurrently...")
        results = await parser.parse_multiple_async(existing_files)

        for result in results:
            if result.success:
                doc = result.document
                print(f"✅ {doc.metadata.file_name}: {len(doc.chunks)} chunks")
            else:
                print(f"❌ Failed: {result.error}")
    else:
        print("ℹ️ No sample files found for concurrent processing demo")


def content_analysis_example():
    """Analyze extracted content in detail"""
    print("\n=== Content Analysis ===")

    parser = RagParser()
    result = parser.parse("sample_document.pdf")

    if not result.success:
        print(f"❌ Error: {result.error}")
        return

    document = result.document

    # Analyze content blocks
    print(f"📋 Content Blocks Analysis:")
    block_types = {}
    for block in document.content_blocks:
        block_type = block.block_type
        block_types[block_type] = block_types.get(block_type, 0) + 1

    for block_type, count in block_types.items():
        print(f"  {block_type}: {count} blocks")

    # Analyze tables
    if document.tables:
        print(f"\n📊 Table Analysis:")
        for i, table in enumerate(document.tables):
            data = table.get("data", [])
            headers = table.get("headers", [])
            print(f"  Table {i+1}: {len(data)} rows, {len(headers)} columns")
            if headers:
                print(f"    Headers: {', '.join(headers[:3])}...")

    # Analyze chunks
    if document.chunks:
        print(f"\n🧩 Chunk Analysis:")
        chunk_sizes = [len(chunk.content) for chunk in document.chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        print(f"  Average chunk size: {avg_size:.0f} characters")
        print(f"  Size range: {min(chunk_sizes)} - {max(chunk_sizes)} characters")

        # Show chunk methods
        chunk_methods = {}
        for chunk in document.chunks:
            method = chunk.metadata.get("chunk_method", "unknown")
            chunk_methods[method] = chunk_methods.get(method, 0) + 1

        for method, count in chunk_methods.items():
            print(f"  {method}: {count} chunks")


def format_support_example():
    """Demonstrate support for different file formats"""
    print("\n=== Format Support Demo ===")

    parser = RagParser()

    # List of sample files to try (replace with your files)
    sample_files = {
        "PDF": "sample.pdf",
        "Word": "sample.docx",
        "PowerPoint": "sample.pptx",
        "Excel": "sample.xlsx",
        "HTML": "sample.html",
        "Markdown": "sample.md",
        "Text": "sample.txt",
        "CSV": "sample.csv",
        "JSON": "sample.json",
    }

    print(f"🔍 Checking format support:")
    supported_formats = parser.get_supported_formats()
    print(f"Supported formats: {', '.join(supported_formats)}")

    for format_name, file_path in sample_files.items():
        if Path(file_path).exists():
            result = parser.parse(file_path)
            if result.success:
                doc = result.document
                print(
                    f"✅ {format_name}: {len(doc.content)} chars, {len(doc.chunks)} chunks"
                )
            else:
                print(f"❌ {format_name}: {result.error}")
        else:
            print(f"ℹ️ {format_name}: Sample file not found ({file_path})")


def chunking_strategy_comparison():
    """Compare different chunking strategies"""
    print("\n=== Chunking Strategy Comparison ===")

    strategies = [
        (ChunkingStrategy.FIXED, "Fixed-size chunking"),
        (ChunkingStrategy.SEMANTIC, "Semantic chunking"),
        (ChunkingStrategy.ADAPTIVE, "Adaptive chunking"),
    ]

    for strategy, description in strategies:
        print(f"\n🔄 Testing {description}...")

        config = ParserConfig(
            chunking_strategy=strategy, chunk_size=1000, chunk_overlap=200
        )

        parser = RagParser(config)
        result = parser.parse("sample_document.pdf")

        if result.success:
            doc = result.document
            chunks = doc.chunks

            if chunks:
                sizes = [len(chunk.content) for chunk in chunks]
                avg_size = sum(sizes) / len(sizes)

                print(f"  📊 Results:")
                print(f"    Chunks created: {len(chunks)}")
                print(f"    Average size: {avg_size:.0f} chars")
                print(f"    Size range: {min(sizes)} - {max(sizes)} chars")

                # Show first chunk metadata
                first_chunk = chunks[0]
                method = first_chunk.metadata.get("chunk_method", "unknown")
                print(f"    Method: {method}")
        else:
            print(f"  ❌ Error: {result.error}")


def main():
    """Run all examples"""
    print("🚀 RAG Parser Examples\n")

    # Check if sample file exists
    sample_file = "sample_document.pdf"
    if not Path(sample_file).exists():
        print(f"ℹ️ Note: Some examples require a sample file '{sample_file}'")
        print(
            "You can replace the file paths in the examples with your own documents.\n"
        )

    # Run examples
    basic_example()
    advanced_configuration_example()
    content_analysis_example()
    format_support_example()
    chunking_strategy_comparison()

    # Run async example
    print("\n🔄 Running async example...")
    asyncio.run(async_processing_example())

    print("\n✅ All examples completed!")


if __name__ == "__main__":
    main()
