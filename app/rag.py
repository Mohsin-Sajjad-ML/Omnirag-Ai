"""
rag.py - Retrieval-Augmented Generation (RAG) core pipeline utilities.

This module provides the core chunking, embedding, vector storage, and retrieval
functions for OmniRAG AI:
1. chunk_text: Splits PDF/DOCX/TXT content into overlapping chunks by word count.
2. chunk_csv_text: Splits structured CSV data into row groups with repeated column headers.
3. embed_and_store: Generates embeddings with sentence-transformers and persists in ChromaDB.
4. search_chunks: Retrieves top-k matching chunks for a user query (ready for Prompt 6).
5. delete_document_chunks: Purges chunks when a document is deleted.

Kept separate from route handlers to ensure modularity, independent testability,
and clear separation of concerns.
"""

import os
import re
import logging
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. PERSISTENT CHROMADB CLIENT CONFIGURATION (PER-USER ISOLATION)
# ==============================================================================
# Directory where ChromaDB data is persisted locally so it survives server restarts.
CHROMA_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_data")
os.makedirs(CHROMA_DATA_DIR, exist_ok=True)

# Persistent Chroma client instance
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)


def get_user_collection_name(username: str) -> str:
    """
    Sanitizes and formats a collection name for a user.
    ChromaDB collection naming constraints:
    - Length between 3 and 63 characters.
    - Starts and ends with an alphanumeric character.
    - Contains only alphanumeric characters, underscores, or hyphens.
    """
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", username).strip("_-")
    if len(clean) < 3:
        clean = f"user_{clean}"
    if not clean[-1].isalnum():
        clean = f"{clean}1"
    return clean[:63]


def get_user_collection(username: str):
    """
    Retrieves or creates a dedicated ChromaDB collection for the specified user.

    ARCHITECTURE DECISION: ONE COLLECTION PER USER
    Instead of dumping all users' documents into a single global collection and
    relying strictly on query filters (which risks accidental cross-tenant data leaks),
    we create a separate ChromaDB collection per user. This guarantees data isolation
    at the database layer by design.
    """
    collection_name = get_user_collection_name(username)
    return chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}  # Cosine similarity for semantic distance
    )


# ==============================================================================
# 2. EMBEDDING MODEL INITIALIZATION (SENTENCE-TRANSFORMERS)
# ==============================================================================
# Load the sentence-transformers embedding model once at module load time (startup).
#
# NOTE ON FIRST-RUN DOWNLOAD & OFFLINE EXECUTION:
# The model 'all-MiniLM-L6-v2' (~80MB) downloads automatically from HuggingFace
# the very first time the application runs and requires an active internet connection
# for that one-time download. Once downloaded, HuggingFace caches the model weights
# locally (typically in ~/.cache/huggingface/hub/). Subsequent server startups and
# runtime embeddings execute 100% locally and fully offline on CPU, without any
# external API calls or API keys.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
logger.info("Loading sentence-transformers model: %s ...", EMBEDDING_MODEL_NAME)
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
logger.info("Sentence-transformers model '%s' loaded successfully.", EMBEDDING_MODEL_NAME)


# ==============================================================================
# 3. TEXT CHUNKING (PDF, DOCX, TXT)
# ==============================================================================

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Splits continuous text (from PDF, DOCX, TXT) into overlapping chunks by word count.

    EXPLANATION FOR NON-TECHNICAL REVIEWERS:
    -----------------------------------------
    1. Why word count instead of raw character count?
       If we split by character count (e.g. every 500 characters), words get sliced
       in half mid-syllable (e.g., 'artificial' becomes 'arti' in one chunk and 'ficial'
       in the next). Splitting by words preserves whole words and grammatically coherent
       phrases, which significantly improves semantic comprehension by the AI.

    2. Why overlap?
       Ideas in documents don't neatly end every 500 words. An answer might start at
       word 490 and finish at word 520. A 50-word sliding overlap ensures that the
       transition between consecutive chunks is captured in both vectors, eliminating
       retrieval 'blind spots' at chunk boundaries.
    """
    if not text or not text.strip():
        return []

    words = text.split()
    if not words:
        return []

    # If total words are within chunk_size, no splitting needed
    if len(words) <= chunk_size:
        return [" ".join(words)]

    step = max(1, chunk_size - overlap)
    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))
        # If we have reached the end of the text, stop
        if start + chunk_size >= len(words):
            break

    return chunks


# ==============================================================================
# 4. CSV STRUCTURED CHUNKING
# ==============================================================================

def chunk_csv_text(text: str, rows_per_chunk: int = 20) -> List[str]:
    """
    Splits structured CSV plain text into row-aware chunks, repeating the table
    column headers at the beginning of each chunk.

    EXPLANATION FOR NON-TECHNICAL REVIEWERS:
    -----------------------------------------
    Why does CSV require a different chunking strategy than PDF/DOCX/TXT?
    Tabular data is structured into rows and columns, not continuous sentences.
    - In Prompt 4, CSV files were converted into structured strings:
        Line 0: [Table Columns (N)]: col1, col2, col3...
        Line 1: Row 1: col1=val1, col2=val2...
        Line 2: Row 2: col1=val3, col2=val4...
    - If we sliced CSV text by word count, individual row records would get cut in half.
    - Even worse, later chunks would have raw values with NO column headers, leaving the
      AI with zero context on what each value means (e.g., is '45' an age, a price, or a quantity?).
    - By grouping whole rows (default 20 rows) and repeating the column schema header at
      the top of every chunk:
        1. Every chunk is completely self-describing.
        2. Semantic vector queries can match both column names and row values accurately.
    """
    if not text or not text.strip():
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    # The first line is the table column header line formatted during ingestion
    header = lines[0]
    data_rows = lines[1:]

    # If the file contains only the header with no data rows
    if not data_rows:
        return [header]

    chunks = []
    for i in range(0, len(data_rows), rows_per_chunk):
        row_batch = data_rows[i : i + rows_per_chunk]
        chunk_content = f"{header}\n" + "\n".join(row_batch)
        chunks.append(chunk_content)

    return chunks


# ==============================================================================
# 5. EMBEDDING GENERATION AND CHROMADB STORAGE
# ==============================================================================

def embed_and_store(
    username: str,
    document_id: int,
    filename: str,
    file_type: str,
    chunks: List[str]
) -> int:
    """
    Generates sentence-transformers embeddings for each text chunk and persists
    them into the user's isolated ChromaDB collection.

    Metadata stored per chunk:
    - document_id (int): Primary key ID referencing SQLite documents table
    - filename (str): Original filename of the document
    - file_type (str): Extension/format (pdf, docx, txt, csv)
    - chunk_index (int): Sequential 0-indexed position within the document

    Returns:
    - int: The number of chunks successfully stored in ChromaDB.
    """
    if not chunks:
        return 0

    collection = get_user_collection(username)

    # 1. Generate 384-dimensional dense embedding vectors using all-MiniLM-L6-v2
    embeddings = embedding_model.encode(
        chunks,
        show_progress_bar=False,
        convert_to_numpy=True
    ).tolist()

    # 2. Prepare chunk IDs and metadata
    ids = [f"doc_{document_id}_chunk_{idx}" for idx in range(len(chunks))]
    metadatas = [
        {
            "document_id": int(document_id),
            "filename": str(filename),
            "file_type": str(file_type),
            "chunk_index": int(idx),
        }
        for idx in range(len(chunks))
    ]

    # Clean up any existing chunks for this document (idempotent re-indexing)
    try:
        collection.delete(where={"document_id": int(document_id)})
    except Exception:
        pass

    # 3. Add chunk text, embeddings, and metadata to ChromaDB
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

    logger.info(
        "Stored %d chunks for document ID %d ('%s') in collection '%s'.",
        len(chunks),
        document_id,
        filename,
        collection.name,
    )

    return len(chunks)


# ==============================================================================
# 6. RETRIEVAL (TOP-K VECTOR SEARCH - READY FOR PROMPT 6)
# ==============================================================================

def search_chunks(
    username: str,
    query: str,
    document_ids: Optional[List[int]] = None,
    top_k: int = 5,
) -> List[dict]:
    """
    Embeds a user query string and retrieves the top-k most relevant chunks from
    the user's isolated ChromaDB collection.

    Optionally filters by a specific list of document_ids.

    Parameters:
    - username: Owner of the collection (ensures multi-tenant data isolation).
    - query: User query text to embed and match.
    - document_ids: Optional list of SQLite document IDs to filter by.
    - top_k: Maximum number of relevant chunks to retrieve (default: 5).

    Returns:
    List of matched chunks with metadata and cosine distances:
    [
        {
            "id": "doc_1_chunk_0",
            "text": "Chunk text content...",
            "document_id": 1,
            "filename": "sample.pdf",
            "file_type": "pdf",
            "chunk_index": 0,
            "distance": 0.142
        },
        ...
    ]
    """
    if not query or not query.strip():
        return []

    collection = get_user_collection(username)

    # If collection is empty, return empty list immediately
    total_docs = collection.count()
    if total_docs == 0:
        return []

    # Generate query embedding
    query_embedding = embedding_model.encode(
        query.strip(),
        show_progress_bar=False,
        convert_to_numpy=True
    ).tolist()

    # Build optional metadata filter
    where_filter = None
    if document_ids is not None and len(document_ids) > 0:
        if len(document_ids) == 1:
            where_filter = {"document_id": int(document_ids[0])}
        else:
            where_filter = {"document_id": {"$in": [int(did) for did in document_ids]}}

    n_results = min(top_k, total_docs)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as exc:
        logger.error("ChromaDB vector search failed: %s", exc)
        return []

    formatted_results = []
    if results and "ids" in results and results["ids"] and len(results["ids"][0]) > 0:
        ids = results["ids"][0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0] if "distances" in results and results["distances"] else [0.0] * len(ids)

        for i in range(len(ids)):
            meta = metas[i] if i < len(metas) and metas[i] else {}
            formatted_results.append({
                "id": ids[i],
                "text": docs[i] if i < len(docs) else "",
                "document_id": meta.get("document_id"),
                "filename": meta.get("filename"),
                "file_type": meta.get("file_type"),
                "chunk_index": meta.get("chunk_index"),
                "distance": dists[i] if i < len(dists) else 0.0,
            })

    return formatted_results


# ==============================================================================
# 7. CLEANUP HELPERS
# ==============================================================================

def delete_document_chunks(username: str, document_id: int) -> None:
    """
    Removes all chunks belonging to a document from the user's Chroma collection.
    Called when a document is deleted from SQLite.
    """
    try:
        collection = get_user_collection(username)
        collection.delete(where={"document_id": int(document_id)})
        logger.info("Deleted chunks for document ID %d from collection '%s'.", document_id, collection.name)
    except Exception as exc:
        logger.warning("Failed to delete chunks for doc %d from Chroma: %s", document_id, exc)


def get_document_chunk_count(username: str, document_id: int) -> int:
    """
    Returns the count of chunks currently stored in ChromaDB for a document.
    """
    try:
        collection = get_user_collection(username)
        res = collection.get(where={"document_id": int(document_id)})
        return len(res.get("ids", []))
    except Exception:
        return 0


# ==============================================================================
# 8. LLM ANSWER GENERATION & RESPONSE FORMATTING (GROQ INTEGRATION)
# ==============================================================================
# Re-exported from app.llm for centralized, backward-compatible access (Prompts 6, 7 & 8).
from app.llm import generate_answer, format_response, FALLBACK_MESSAGE, generate_summary
