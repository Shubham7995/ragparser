"""
LlamaIndex integration adapter for RAG Parser
"""

from typing import List, Optional, Union, Any, Dict
from pathlib import Path
import logging

try:
    from llama_index.core import Document
    from llama_index.core.readers.base import BaseReader
    from llama_index.core.schema import NodeRelationship, RelatedNodeInfo

    HAS_LLAMAINDEX = True
except ImportError:
    try:
        # Fallback for older LlamaIndex versions
        from llama_index import Document
        from llama_index.readers.base import BaseReader
        from llama_index.schema import NodeRelationship, RelatedNodeInfo

        HAS_LLAMAINDEX = True
    except ImportError:
        HAS_LLAMAINDEX = False

        # Create dummy classes for type hints
        class Document:
            pass

        class BaseReader:
            pass

        class NodeRelationship:
            pass

        class RelatedNodeInfo:
            pass


from ..core.parser import RagParser
from ..core.models import ParserConfig, ParsedDocument, ChunkResult


class RagParserReader(BaseReader):
    """LlamaIndex reader using RAG Parser"""

    def __init__(
        self,
        config: Optional[ParserConfig] = None,
        include_metadata: bool = True,
        chunk_mode: bool = True,
        add_relationships: bool = True,
    ):
        """
        Initialize LlamaIndex reader

        Args:
            config: Parser configuration
            include_metadata: Whether to include metadata in documents
            chunk_mode: If True, return chunks; if False, return full document
            add_relationships: Whether to add relationships between chunks
        """
        if not HAS_LLAMAINDEX:
            raise ImportError(
                "LlamaIndex integration requires llama-index. "
                "Install with: pip install llama-index"
            )

        super().__init__()
        self.config = config or ParserConfig()
        self.include_metadata = include_metadata
        self.chunk_mode = chunk_mode
        self.add_relationships = add_relationships
        self.parser = RagParser(self.config)

    def load_data(
        self,
        file: Union[str, Path, List[Union[str, Path]]],
        extra_info: Optional[Dict] = None,
    ) -> List[Document]:
        """
        Load documents using RAG Parser

        Args:
            file: Path to file(s) or list of paths
            extra_info: Additional metadata to include

        Returns:
            List of LlamaIndex Documents
        """
        documents = []
        file_paths = self._normalize_paths(file)

        for file_path in file_paths:
            try:
                result = self.parser.parse(file_path)

                if result.success:
                    if self.chunk_mode:
                        # Return chunks as separate documents
                        chunk_docs = self._create_chunk_documents(
                            result.document, file_path, extra_info
                        )
                        documents.extend(chunk_docs)
                    else:
                        # Return full document
                        doc = self._create_document(
                            result.document, file_path, extra_info
                        )
                        documents.append(doc)
                else:
                    logging.error(f"Failed to parse {file_path}: {result.error}")

            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
                continue

        return documents

    def _normalize_paths(
        self, file: Union[str, Path, List[Union[str, Path]]]
    ) -> List[Path]:
        """Normalize file paths to list of Path objects"""
        if isinstance(file, (str, Path)):
            path = Path(file)
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
            return [Path(p) for p in file]

    def _create_document(
        self,
        parsed_doc: ParsedDocument,
        file_path: Path,
        extra_info: Optional[Dict] = None,
    ) -> Document:
        """Create LlamaIndex Document from ParsedDocument"""
        metadata = {}

        if self.include_metadata:
            # Include document metadata
            metadata.update(
                {
                    "file_path": str(file_path),
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

        # Add extra info
        if extra_info:
            metadata.update(extra_info)

        return Document(
            text=parsed_doc.content,
            metadata=metadata,
            doc_id=f"{file_path.stem}_{hash(str(file_path))}",
        )

    def _create_chunk_documents(
        self,
        parsed_doc: ParsedDocument,
        file_path: Path,
        extra_info: Optional[Dict] = None,
    ) -> List[Document]:
        """Create LlamaIndex Documents from chunks"""
        documents = []

        for i, chunk in enumerate(parsed_doc.chunks):
            metadata = {}

            if self.include_metadata:
                # Base metadata for all chunks
                metadata.update(
                    {
                        "file_path": str(file_path),
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

            # Add extra info
            if extra_info:
                metadata.update(extra_info)

            doc_id = f"{file_path.stem}_{hash(str(file_path))}_{i}"

            document = Document(text=chunk.content, metadata=metadata, doc_id=doc_id)

            documents.append(document)

        # Add relationships between chunks if enabled
        if self.add_relationships and len(documents) > 1:
            documents = self._add_chunk_relationships(documents)

        return documents

    def _add_chunk_relationships(self, documents: List[Document]) -> List[Document]:
        """Add relationships between chunk documents"""

        for i, doc in enumerate(documents):
            relationships = {}

            # Add previous chunk relationship
            if i > 0:
                prev_doc = documents[i - 1]
                relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(
                    node_id=prev_doc.doc_id, metadata={"chunk_index": i - 1}
                )

            # Add next chunk relationship
            if i < len(documents) - 1:
                next_doc = documents[i + 1]
                relationships[NodeRelationship.NEXT] = RelatedNodeInfo(
                    node_id=next_doc.doc_id, metadata={"chunk_index": i + 1}
                )

            # Add parent document relationship
            parent_id = f"{doc.metadata.get('file_name', 'unknown')}_{hash(doc.metadata.get('file_path', ''))}"
            relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
                node_id=parent_id,
                metadata={"document_title": doc.metadata.get("document_title", "")},
            )

            # Set relationships
            doc.relationships = relationships

        return documents


class RagParserNodeParser:
    """Node parser that uses RAG Parser chunking strategies"""

    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize node parser

        Args:
            config: Parser configuration for chunking
        """
        if not HAS_LLAMAINDEX:
            raise ImportError(
                "LlamaIndex integration requires llama-index. "
                "Install with: pip install llama-index"
            )

        self.config = config or ParserConfig()
        self.parser = RagParser(self.config)

    def get_nodes_from_documents(
        self, documents: List[Document], show_progress: bool = False
    ) -> List[Any]:  # Returns List[BaseNode] but avoiding import complexity
        """Parse documents into nodes using RAG Parser chunking"""

        try:
            from llama_index.core.schema import TextNode
        except ImportError:
            from llama_index.schema import TextNode

        nodes = []

        for doc in documents:
            try:
                # Parse document text using RAG Parser
                result = self.parser.parse_from_bytes(
                    doc.text.encode("utf-8"),
                    doc.metadata.get("file_name", "document.txt"),
                )

                if result.success and result.document.chunks:
                    # Convert chunks to TextNodes
                    for i, chunk in enumerate(result.document.chunks):
                        metadata = doc.metadata.copy()
                        metadata.update(
                            {
                                "chunk_id": chunk.chunk_id,
                                "chunk_index": i,
                                "chunk_token_count": chunk.token_count,
                                "total_chunks": len(result.document.chunks),
                                "embedding_ready": chunk.embedding_ready,
                            }
                        )
                        metadata.update(chunk.metadata)

                        node = TextNode(
                            text=chunk.content, metadata=metadata, id_=chunk.chunk_id
                        )

                        # Add relationships if original document had them
                        if hasattr(doc, "relationships") and doc.relationships:
                            node.relationships = doc.relationships.copy()

                        nodes.append(node)

                else:
                    # Fallback: create single node from document
                    node = TextNode(
                        text=doc.text,
                        metadata=doc.metadata,
                        id_=doc.doc_id or f"fallback_{hash(doc.text)}",
                    )
                    nodes.append(node)

            except Exception as e:
                logging.error(f"Error parsing document: {str(e)}")
                # Fallback: create single node
                node = TextNode(
                    text=doc.text,
                    metadata=doc.metadata,
                    id_=doc.doc_id or f"error_fallback_{hash(doc.text)}",
                )
                nodes.append(node)

        return nodes


# Convenience functions
def load_documents_llamaindex(
    file_path: Union[str, Path, List[Union[str, Path]]],
    config: Optional[ParserConfig] = None,
    **kwargs,
) -> List[Document]:
    """
    Convenience function to load documents for LlamaIndex

    Args:
        file_path: Path to file(s) or directory
        config: Parser configuration
        **kwargs: Additional arguments for RagParserReader

    Returns:
        List of LlamaIndex Documents
    """
    reader = RagParserReader(config, **kwargs)
    return reader.load_data(file_path)


def create_node_parser_llamaindex(
    config: Optional[ParserConfig] = None,
) -> RagParserNodeParser:
    """
    Convenience function to create node parser for LlamaIndex

    Args:
        config: Parser configuration

    Returns:
        RagParserNodeParser instance
    """
    return RagParserNodeParser(config)
