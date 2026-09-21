"""
rag/service.py - Retrieval-Augmented Generation (RAG) core pipeline utilities.

Provides chunking, embedding, vector storage in ChromaDB, and similarity search.
"""
from langfuse import observe

import os
import re
import logging
from typing import List, Optional

import chromadb
from sentence_transformers import SentenceTransformer

from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import Document

logger = logging.getLogger(__name__)

# Directory where ChromaDB data is persisted locally (backend/chroma_data)
CHROMA_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_data")
os.makedirs(CHROMA_DATA_DIR, exist_ok=True)

# Persistent Chroma client instance
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)


def get_user_collection_name(clerk_user_id: str) -> str:
    """
    Sanitizes and formats a collection name for a user.
    ChromaDB collection naming constraints:
    - Length between 3 and 63 characters.
    - Starts and ends with an alphanumeric character.
    - Contains only alphanumeric characters, underscores, or hyphens.
    """
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", clerk_user_id).strip("_-")
    if len(clean) < 3:
        clean = f"user_{clean}"
    if not clean[-1].isalnum():
        clean = f"{clean}1"
    return clean[:63]


def get_user_collection(clerk_user_id: str):
    """
    Retrieves or creates a dedicated ChromaDB collection for the specified user.
    """
    collection_name = get_user_collection_name(clerk_user_id)
    return chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}  # Cosine similarity for semantic distance
    )


# Load the sentence-transformers embedding model
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
logger.info("Loading sentence-transformers model: %s ...", EMBEDDING_MODEL_NAME)
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
logger.info("Sentence-transformers model '%s' loaded successfully.", EMBEDDING_MODEL_NAME)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Splits continuous text (from PDF, DOCX, TXT) into overlapping chunks by word count.
    """
    if not text or not text.strip():
        return []

    words = text.split()
    if not words:
        return []

    if len(words) <= chunk_size:
        return [" ".join(words)]

    step = max(1, chunk_size - overlap)
    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break

    return chunks


def chunk_csv_text(text: str, rows_per_chunk: int = 20) -> List[str]:
    """
    Splits structured CSV plain text into row-aware chunks, repeating the table
    column headers at the beginning of each chunk.
    """
    if not text or not text.strip():
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    header = lines[0]
    data_rows = lines[1:]

    if not data_rows:
        return [header]

    chunks = []
    for i in range(0, len(data_rows), rows_per_chunk):
        row_batch = data_rows[i : i + rows_per_chunk]
        chunk_content = f"{header}\n" + "\n".join(row_batch)
        chunks.append(chunk_content)

    return chunks


def embed_and_store(
    clerk_user_id: Optional[str] = None,
    document_id: int = 0,
    filename: str = "",
    file_type: str = "",
    chunks: Optional[List[str]] = None,
    username: Optional[str] = None,
) -> int:
    """
    Generates sentence-transformers embeddings for each text chunk and persists
    them into the user's isolated ChromaDB collection.
    """
    owner_id = clerk_user_id or username
    if not owner_id or not chunks:
        return 0

    collection = get_user_collection(owner_id)

    embeddings = embedding_model.encode(
        chunks,
        show_progress_bar=False,
        convert_to_numpy=True
    ).tolist()

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

    try:
        collection.delete(where={"document_id": int(document_id)})
    except Exception:
        pass

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


@observe(name="embedding")
def embed_query(query: str) -> List[float]:
    """Generates the dense vector embedding for the search query."""
    return embedding_model.encode(
        query.strip(),
        show_progress_bar=False,
        convert_to_numpy=True
    ).tolist()


@observe(name="retrieval")
def vector_search(
    collection,
    query_embedding: List[float],
    n_results: int,
    where_filter: Optional[dict] = None,
) -> dict:
    """Executes similarity search on the user's ChromaDB collection."""
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )


def search_chunks(
    clerk_user_id: Optional[str] = None,
    query: str = "",
    document_ids: Optional[List[int]] = None,
    top_k: int = 5,
    username: Optional[str] = None,
) -> List[dict]:
    """
    Embeds a user query string and retrieves the top-k most relevant chunks from
    the user's isolated ChromaDB collection.
    """
    owner_id = clerk_user_id or username
    if not owner_id or not query or not query.strip():
        return []

    collection = get_user_collection(owner_id)

    total_docs = collection.count()
    if total_docs == 0:
        return []

    query_embedding = embed_query(query)

    where_filter = None
    if document_ids is not None and len(document_ids) > 0:
        if len(document_ids) == 1:
            where_filter = {"document_id": int(document_ids[0])}
        else:
            where_filter = {"document_id": {"$in": [int(did) for did in document_ids]}}

    n_results = min(top_k, total_docs)

    try:
        results = vector_search(
            collection=collection,
            query_embedding=query_embedding,
            n_results=n_results,
            where_filter=where_filter,
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


def term_present_in_document(
    term: str,
    clerk_user_id: Optional[str] = None,
    document_ids: list[int] | None = None,
    username: Optional[str] = None,
    db: Optional[Session] = None,
) -> bool:
    """Check literal term presence in the user's stored full document text."""
    normalized_term = (term or "").strip().casefold()
    if not normalized_term:
        return False

    owner_id = clerk_user_id or username
    if not owner_id:
        return False

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        query = db.query(Document).filter(
            Document.clerk_user_id == owner_id,
            Document.status == "indexed",
        )
        if document_ids is not None:
            if not document_ids:
                return False
            query = query.filter(Document.id.in_(document_ids))

        return any(
            normalized_term in (document.extracted_text or "").casefold()
            for document in query.all()
        )
    finally:
        if close_db:
            db.close()


def get_document_snippets_for_term(
    term: str,
    clerk_user_id: Optional[str] = None,
    document_ids: list[int] | None = None,
    username: Optional[str] = None,
    max_snippets_per_doc: int = 3,
    db: Optional[Session] = None,
) -> list[dict]:
    """
    Extract context snippets from documents where the term is mentioned,
    along with document metadata (filename, id, file_type).
    """
    normalized_term = (term or "").strip().casefold()
    if not normalized_term:
        return []

    owner_id = clerk_user_id or username
    if not owner_id:
        return []

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        query = db.query(Document).filter(
            Document.clerk_user_id == owner_id,
            Document.status == "indexed",
        )
        if document_ids is not None:
            if not document_ids:
                return []
            query = query.filter(Document.id.in_(document_ids))

        results = []
        for document in query.all():
            text = document.extracted_text or ""
            if normalized_term not in text.casefold():
                continue

            lines = text.split("\n")
            matching_snippets = []
            for i, line in enumerate(lines):
                if normalized_term in line.casefold():
                    start = max(0, i - 2)
                    end = min(len(lines), i + 5)
                    snippet = "\n".join(lines[start:end]).strip()
                    if snippet and snippet not in matching_snippets:
                        matching_snippets.append(snippet)
                    if len(matching_snippets) >= max_snippets_per_doc:
                        break

            if matching_snippets:
                results.append({
                    "document_id": document.id,
                    "filename": document.original_filename,
                    "file_type": document.file_type,
                    "snippets": matching_snippets,
                    "context_text": "\n---\n".join(matching_snippets),
                })
        return results
    finally:
        if close_db:
            db.close()


def delete_document_chunks(
    clerk_user_id: Optional[str] = None,
    document_id: int = 0,
    username: Optional[str] = None,
) -> None:
    """
    Removes all chunks belonging to a document from the user's Chroma collection.
    """
    owner_id = clerk_user_id or username
    if not owner_id:
        return
    try:
        collection = get_user_collection(owner_id)
        collection.delete(where={"document_id": int(document_id)})
        logger.info("Deleted chunks for document ID %d from collection '%s'.", document_id, collection.name)
    except Exception as exc:
        logger.warning("Failed to delete chunks for doc %d from Chroma: %s", document_id, exc)


def get_document_chunk_count(
    clerk_user_id: Optional[str] = None,
    document_id: int = 0,
    username: Optional[str] = None,
) -> int:
    """
    Returns the count of chunks currently stored in ChromaDB for a document.
    """
    owner_id = clerk_user_id or username
    if not owner_id:
        return 0
    try:
        collection = get_user_collection(owner_id)
        res = collection.get(where={"document_id": int(document_id)})
        return len(res.get("ids", []))
    except Exception:
        return 0


def delete_user_collection(
    clerk_user_id: Optional[str] = None,
    username: Optional[str] = None,
) -> None:
    """
    Deletes the entire ChromaDB collection for the user when their account is deleted.
    """
    owner_id = clerk_user_id or username
    if not owner_id:
        return
    try:
        collection_name = get_user_collection_name(owner_id)
        chroma_client.delete_collection(name=collection_name)
        logger.info("Purged ChromaDB collection '%s' for user '%s'.", collection_name, owner_id)
    except Exception as exc:
        logger.warning("Could not delete ChromaDB collection for user '%s': %s", owner_id, exc)


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
    "SessionLocal",
]
