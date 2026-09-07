"""
security.py - Password hashing and verification utilities.

Uses passlib with bcrypt algorithm to securely hash user passwords
before storing them in the database, and to verify plain-text passwords
during login attempts.
"""

from passlib.context import CryptContext

# Passlib configuration for password hashing using bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.
    
    Args:
        password (str): Plain-text password to hash.
        
    Returns:
        str: Securely hashed bcrypt password string.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.
    
    Args:
        plain_password (str): Plain-text password provided by user during login.
        hashed_password (str): Stored bcrypt password hash from database.
        
    Returns:
        bool: True if password matches hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)
