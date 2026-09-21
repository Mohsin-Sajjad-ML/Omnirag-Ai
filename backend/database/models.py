"""
models.py - SQLAlchemy ORM Models.

Defines the relational database structure (tables and columns) for OmniRAG AI:
- User: Relational user record keyed by clerk_user_id.
- FaceDescriptor: Biometric face embeddings per user.
- Document: Parsed text and RAG chunk status per document.
- ChatSession: Conversation sessions per user.
- ChatMessage: Individual user queries and assistant responses with citations.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class User(Base):
    """
    User model representing the 'users' table in SQLite.
    
    Fields:
    - id: Primary Key integer auto-incremented.
    - clerk_user_id: Clerk user ID used as the ownership identifier.
    - face_descriptor: Text column for future facial recognition data (nullable).
    - created_at: UTC timestamp when the user account was created.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    clerk_user_id = Column(String(255), unique=True, index=True, nullable=False)
    face_descriptor = Column(Text, nullable=True, default=None)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    face_descriptors = relationship(
        "FaceDescriptor",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="FaceDescriptor.created_at"
    )


class FaceDescriptor(Base):
    """
    FaceDescriptor model representing the 'face_descriptors' table in SQLite.
    Stores biometric face embeddings per user (supports multiple registered faces).

    Fields:
    - id: Primary Key integer auto-incremented.
    - clerk_user_id: Clerk user ID of the owner.
    - descriptor: JSON-serialized 128-dimensional embedding vector.
    - label: Human-readable label (e.g. "Primary Face", "Office Face").
    - created_at: UTC timestamp when the face was registered.
    """
    __tablename__ = "face_descriptors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    clerk_user_id = Column(String(255), ForeignKey("users.clerk_user_id", ondelete="CASCADE"), index=True, nullable=False)
    descriptor = Column(Text, nullable=False)
    label = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="face_descriptors")


class Document(Base):
    """
    Document model representing the 'documents' table in SQLite.
    Stores raw parsed text extracted from uploaded files associated with a user account.
    
    Fields:
    - id: Primary Key integer auto-incremented.
    - clerk_user_id: Clerk user ID identifying the owner of the document.
    - original_filename: Original name of the uploaded file.
    - file_type: Extension/type ("pdf", "docx", "txt", or "csv").
    - upload_timestamp: UTC timestamp when the file was uploaded and processed.
    - extracted_text: Plain text content parsed from the document (nullable).
    - status: Processing status ("parsed", "indexed", or "failed").
    - chunk_count: Number of text chunks stored in ChromaDB vector store.
    - summary: AI-generated summary of the document text (nullable, Prompt 8).
    - error_message: Error description if parsing or indexing failed (nullable).
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    clerk_user_id = Column(String(255), index=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    upload_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    extracted_text = Column(Text, nullable=True)
    status = Column(String(20), nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    summary = Column(Text, nullable=True, default=None)
    error_message = Column(Text, nullable=True)


class ChatSession(Base):
    """
    ChatSession model representing the 'chat_sessions' table in SQLite.
    Stores user conversation sessions for multi-turn chat history.
    
    Fields:
    - id: Primary Key integer auto-incremented.
    - clerk_user_id: Clerk user ID identifying the owner of the chat session.
    - title: Human-readable topic or auto-generated title for the session.
    - created_at: UTC timestamp when the session was created.
    """
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    clerk_user_id = Column(String(255), index=True, nullable=False)
    title = Column(String(255), nullable=False, default="New Chat")
    pinned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    """
    ChatMessage model representing the 'chat_messages' table in SQLite.
    Stores individual dialogue turns (user query and assistant response).
    
    Fields:
    - id: Primary Key integer auto-incremented.
    - session_id: Foreign key linking the message to a chat_session.
    - role: Dialogue role ("user" or "assistant").
    - content: Plain text content of the message.
    - citations: JSON-serialized list of source citations for assistant messages (nullable).
    - is_fallback: Flag indicating whether this assistant answer was a fallback response.
    - response_language: Language code for text-to-speech selection ("en" or "roman-ur").
    - created_at: UTC timestamp when the message was sent/generated.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    citations = Column(Text, nullable=True, default=None)
    is_fallback = Column(Boolean, default=False, nullable=False)
    source = Column(String(30), nullable=True, default="rag")
    response_language = Column(String(20), nullable=True, default="en")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("ChatSession", back_populates="messages")
