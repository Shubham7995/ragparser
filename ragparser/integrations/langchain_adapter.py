"""
LangChain integration adapter for RAG Parser
"""

from typing import List, Optional, Iterator, Union
from pathlib import Path
import logging

try:
    from langchain.schema import Document
    from langchain.document_loaders.base import BaseLoader

    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

    # Create dummy classes for type hints
    class Document:
        pass

    class BaseLoader:
        pass


from ..core.parser import RagParser
from ..core.models import ParserConfig, ParsedDocument, ChunkResult


class RagParserLoader(BaseLoader):
    """LangChain document loader using RAG Parser"""

    def __init__(
        self,
        file_path: Union[str, Path, List[Union[str, Path]]],
        config: Optional[ParserConfig] = None,
        include_metadata: bool = True,
        chunk_mode: bool = True,
    ):
        """
        Initialize LangChain loader

        Args:
            file_path: Path to file(s) or directory
            config: Parser configuration
            include_metadata: Whether to include metadata in documents
            chunk_mode: If True, return chunks; if False, return full document
        """
        if not HAS_LANGCHAIN:
            raise ImportError(
                "LangChain integration requires langchain. "
                "Install with: pip install langchain"
            )

        self.file_paths = self._normalize_paths(file_path)
        self.config = config or ParserConfig()
        self.include_metadata = include_metadata
        self.chunk_mode = chunk_mode
        self.parser = RagParser(self.config)

    def _normalize_paths(
        self, file_path: Union[str, Path, List[Union[str, Path]]]
    ) -> List[Path]:
        """Normalize file paths to list of Path objects"""
        if isinstance(file_path, (str, Path)):
            path = Path(file_path)
            if path.is_dir():
                # Load all supported files from directory
                paths = []
                for ext in [
                    ".pdf",
                    ".docx",
                    ".pptx",
                    ".xlsx",
                    ".html",
                    ".md",
                    ".txt",
                    ".csv",
                    ".json",
                ]:
                    paths.extend(path.glob(f"*{ext}"))
                    paths.extend(path.glob(f"**/*{ext}"))  # Recursive
                return sorted(set(paths))
            else:
                return [path]
        else:
            return [Path(p) for p in file_path]

    def load(self) -> List[Document]:
        """Load documents using RAG Parser"""
        documents = []

        for file_path in self.file_paths:
            try:
                result = self.parser.parse(file_path)

                if result.success:
                    if self.chunk_mode:
                        # Return chunks as separate documents
                        documents.extend(
                            self._create_chunk_documents(result.document, file_path)
                        )
                    else:
                        # Return full document
                        documents.append(
                            self._create_document(result.document, file_path)
                        )
                else:
                    logging.error(f"Failed to parse {file_path}: {result.error}")

            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
                continue

        return documents

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load documents one by one"""
        for file_path in self.file_paths:
            try:
                result = self.parser.parse(file_path)

                if result.success:
                    if self.chunk_mode:
                        # Yield chunks one by one
                        for doc in self._create_chunk_documents(
                            result.document, file_path
                        ):
                            yield doc
                    else:
                        # Yield full document
                        yield self._create_document(result.document, file_path)
                else:
                    logging.error(f"Failed to parse {file_path}: {result.error}")

            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
                continue

    def _create_document(self, parsed_doc: ParsedDocument, file_path: Path) -> Document:
        """Create LangChain Document from ParsedDocument"""
        metadata = {}

        if self.include_metadata:
            # Include document metadata
            metadata.update(
                {
                    "source": str(file_path),
                    "file_name": parsed_doc.metadata.file_name,
                    "file_type": parsed_doc.metadata.file_type.value,
                    "file_size": parsed_doc.metadata.file_size,
                    "page_count": parsed_doc.metadata.page_count,
                    "word_count": parsed_doc.metadata.word_count,
                    "character_count": parsed_doc.metadata.character_count,
                    "processing_time": parsed_doc.processing_time,
                    "chunk_count": len(parsed_doc.chunks),
                    "table_count": len(parsed_doc.tables),
                    "image_count": len(parsed_doc.images),
                    "link_count": len(parsed_doc.links),
                }
            )

            # Include document-specific metadata
            if parsed_doc.metadata.title:
                metadata["title"] = parsed_doc.metadata.title
            if parsed_doc.metadata.author:
                metadata["author"] = parsed_doc.metadata.author
            if parsed_doc.metadata.subject:
                metadata["subject"] = parsed_doc.metadata.subject
            if parsed_doc.metadata.creation_date:
                metadata["creation_date"] = (
                    parsed_doc.metadata.creation_date.isoformat()
                )
            if parsed_doc.metadata.modification_date:
                metadata["modification_date"] = (
                    parsed_doc.metadata.modification_date.isoformat()
                )

        return Document(page_content=parsed_doc.content, metadata=metadata)

    def _create_chunk_documents(
        self, parsed_doc: ParsedDocument, file_path: Path
    ) -> List[Document]:
        """Create LangChain Documents from chunks"""
        documents = []

        for i, chunk in enumerate(parsed_doc.chunks):
            metadata = {}

            if self.include_metadata:
                # Base metadata for all chunks
                metadata.update(
                    {
                        "source": str(file_path),
                        "file_name": parsed_doc.metadata.file_name,
                        "file_type": parsed_doc.metadata.file_type.value,
                        "chunk_id": chunk.chunk_id,
                        "chunk_index": i,
                        "chunk_token_count": chunk.token_count,
                        "total_chunks": len(parsed_doc.chunks),
                        "source_blocks": chunk.source_blocks,
                        "embedding_ready": chunk.embedding_ready,
                    }
                )

                # Chunk position information
                if chunk.start_char is not None:
                    metadata["start_char"] = chunk.start_char
                if chunk.end_char is not None:
                    metadata["end_char"] = chunk.end_char

                # Include chunk-specific metadata
                metadata.update(chunk.metadata)

                # Document-level metadata
                if parsed_doc.metadata.title:
                    metadata["document_title"] = parsed_doc.metadata.title
                if parsed_doc.metadata.author:
                    metadata["document_author"] = parsed_doc.metadata.author
                if parsed_doc.metadata.page_count:
                    metadata["document_page_count"] = parsed_doc.metadata.page_count

            documents.append(Document(page_content=chunk.content, metadata=metadata))

        return documents


class RagParserTextSplitter:
    """Text splitter that uses RAG Parser chunking strategies"""

    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize text splitter

        Args:
            config: Parser configuration for chunking
        """
        if not HAS_LANGCHAIN:
            raise ImportError(
                "LangChain integration requires langchain. "
                "Install with: pip install langchain"
            )

        self.config = config or ParserConfig()
        self.parser = RagParser(self.config)

    def split_text(self, text: str) -> List[str]:
        """Split text using RAG Parser chunking"""
        try:
            # Create a temporary document for chunking
            from ..core.models import DocumentMetadata, FileType

            # Create minimal document
            document = ParsedDocument(
                content=text,
                metadata=DocumentMetadata(
                    file_name="text_input",
                    file_type=FileType.TXT,
                    file_size=len(text.encode("utf-8")),
                ),
            )

            # Get chunker and chunk the content
            from ..chunkers import get_chunker

            chunker = get_chunker(self.config.chunking_strategy)

            if chunker:
                import asyncio

                chunks = asyncio.run(chunker.chunk_async(document, self.config))
                return [chunk.content for chunk in chunks]
            else:
                # Fallback to simple splitting
                return [text]

        except Exception as e:
            logging.error(f"Error in text splitting: {str(e)}")
            return [text]

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split LangChain documents using RAG Parser"""
        split_docs = []

        for doc in documents:
            chunks = self.split_text(doc.page_content)

            for i, chunk in enumerate(chunks):
                # Create new document with chunk content
                chunk_metadata = doc.metadata.copy()
                chunk_metadata.update(
                    {
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "chunk_method": self.config.chunking_strategy.value,
                    }
                )

                split_docs.append(Document(page_content=chunk, metadata=chunk_metadata))

        return split_docs


# Convenience functions for easier import
def load_documents(
    file_path: Union[str, Path, List[Union[str, Path]]],
    config: Optional[ParserConfig] = None,
    **kwargs,
) -> List[Document]:
    """
    Convenience function to load documents

    Args:
        file_path: Path to file(s) or directory
        config: Parser configuration
        **kwargs: Additional arguments for RagParserLoader

    Returns:
        List of LangChain Documents
    """
    loader = RagParserLoader(file_path, config, **kwargs)
    return loader.load()


def create_text_splitter(
    config: Optional[ParserConfig] = None,
) -> RagParserTextSplitter:
    """
    Convenience function to create text splitter

    Args:
        config: Parser configuration

    Returns:
        RagParserTextSplitter instance
    """
    return RagParserTextSplitter(config)
