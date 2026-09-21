"""
connection.py - Database connection and session management setup.

This module initializes the SQLite database connection using SQLAlchemy.
It defines the database engine, session factory, declarative base, and
a database session dependency for FastAPI routes.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import settings

# SQLite local database connection URL
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create SQLAlchemy engine instance
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal is a class factory for generating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class from which all SQLAlchemy database models inherit
Base = declarative_base()


def get_db():
    """
    Dependency function to provide a database session per HTTP request.
    Automatically ensures the database session is closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
