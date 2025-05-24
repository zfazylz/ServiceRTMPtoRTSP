"""
SQLite database module for storing stream information using SQLAlchemy.

This module provides functions for creating, reading, updating, and deleting
stream information in a SQLite database using SQLAlchemy ORM.

This is a compatibility layer that re-exports functionality from the database package.
"""

# Re-export all necessary functions and classes from the database package
from app.database import (
    Stream,
    Base,
    get_db,
    init_db,
    save_stream,
    update_stream,
    delete_stream,
    get_stream,
    get_all_streams,
)

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
