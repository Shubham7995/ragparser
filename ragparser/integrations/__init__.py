"""Framework integration adapters"""

__all__ = []

# LangChain integration
try:
    from .langchain_adapter import (
        RagParserLoader,
        RagParserTextSplitter,
        load_documents,
        create_text_splitter,
    )

    __all__.extend(
        [
            "RagParserLoader",
            "RagParserTextSplitter",
            "load_documents",
            "create_text_splitter",
        ]
    )
except ImportError:
    pass

# LlamaIndex integration
try:
    from .llamaindex_adapter import (
        RagParserReader,
        RagParserNodeParser,
        load_documents_llamaindex,
        create_node_parser_llamaindex,
    )

    __all__.extend(
        [
            "RagParserReader",
            "RagParserNodeParser",
            "load_documents_llamaindex",
            "create_node_parser_llamaindex",
        ]
    )
except ImportError:
    pass
