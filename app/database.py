"""
database.py - Database connection and session management setup.

This module initializes the SQLite database connection using SQLAlchemy.
It defines the database engine, session factory, base model class, and
a database session dependency for FastAPI routes.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite local database connection URL
# Stores database tables in 'sql_app.db' in the project root directory
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

# Create SQLAlchemy engine instance
# connect_args={"check_same_thread": False} is required for SQLite in FastAPI
# so multiple threads can interact with the same database connection if needed.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal is a class factory for generating database sessions
# autocommit=False ensures transactions are explicitly committed
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class from which all SQLAlchemy database models will inherit
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
