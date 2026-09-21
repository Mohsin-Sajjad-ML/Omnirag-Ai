"""
backend.rag - Retrieval-Augmented Generation (RAG) feature domain.
"""
from backend.rag.service import (
    CHROMA_DATA_DIR,
    chroma_client,
    get_user_collection_name,
    get_user_collection,
    EMBEDDING_MODEL_NAME,
    embedding_model,
    chunk_text,
    chunk_csv_text,
    embed_and_store,
    embed_query,
    vector_search,
    search_chunks,
    term_present_in_document,
    get_document_snippets_for_term,
    delete_document_chunks,
    get_document_chunk_count,
    delete_user_collection,
)

__all__ = [
    "CHROMA_DATA_DIR",
    "chroma_client",
    "get_user_collection_name",
    "get_user_collection",
    "EMBEDDING_MODEL_NAME",
    "embedding_model",
    "chunk_text",
    "chunk_csv_text",
    "embed_and_store",
    "embed_query",
    "vector_search",
    "search_chunks",
    "term_present_in_document",
    "get_document_snippets_for_term",
    "delete_document_chunks",
    "get_document_chunk_count",
    "delete_user_collection",
]
