"""
Database session management.

This module provides functions for creating and managing database sessions.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.models import Base

# Database file path
DB_DIR = os.path.join(os.getcwd(), 'data')
DB_PATH = os.path.join(DB_DIR, 'streams.db')

# Ensure the data directory exists
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# Create SQLAlchemy engine
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Get a database session."""
    db = SessionLocal()
    try:
        return db
    except:
        db.close()
        raise


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)
