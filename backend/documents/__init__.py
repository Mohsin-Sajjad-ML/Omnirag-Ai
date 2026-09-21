"""
Documents domain package.
"""

from backend.documents.parsing_service import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    parse_pdf_file,
    parse_docx_file,
    parse_txt_file,
    parse_csv_file,
    extract_document_text,
)
from backend.documents.rag_service import (
    get_user_collection,
    search_chunks,
    embed_and_store,
    delete_document_chunks,
)
from backend.documents.router import (
    router,
    upload_document,
    get_document_chunk,
    get_user_documents,
    delete_document,
)

__all__ = [
    "ALLOWED_EXTENSIONS",
    "MAX_FILE_SIZE_BYTES",
    "parse_pdf_file",
    "parse_docx_file",
    "parse_txt_file",
    "parse_csv_file",
    "extract_document_text",
    "get_user_collection",
    "search_chunks",
    "embed_and_store",
    "delete_document_chunks",
    "router",
    "upload_document",
    "get_document_chunk",
    "get_user_documents",
    "delete_document",
]
