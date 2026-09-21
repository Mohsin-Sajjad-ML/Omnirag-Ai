"""
Authentication and user management domain package.
"""

from clerk_backend_api import Clerk
from backend.auth.router import router

__all__ = ["router", "Clerk"]
