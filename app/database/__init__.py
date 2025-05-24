"""
Database package for the application.

This package provides database models, session management, and CRUD operations.
"""

# Import CRUD operations
from app.database.crud import (
    save_stream,
    update_stream,
    delete_stream,
    get_stream,
    get_all_streams,
)
# Import models
from app.database.models import Stream, Base
# Import session management
from app.database.session import get_db, init_db

# Initialize the database when the package is imported
init_db()

# Export all necessary functions and classes
__all__ = [
    'Stream',
    'Base',
    'get_db',
    'init_db',
    'save_stream',
    'update_stream',
    'delete_stream',
    'get_stream',
    'get_all_streams',
]
