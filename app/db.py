"""
SQLite database module for storing stream information using SQLAlchemy.

This module provides functions for creating, reading, updating, and deleting
stream information in a SQLite database using SQLAlchemy ORM.
"""

import os
import datetime
from typing import List, Dict, Optional, Tuple

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

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

# Create base class for models
Base = declarative_base()

# Define Stream model
class Stream(Base):
    """SQLAlchemy model for streams table."""
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    stream_name = Column(String, unique=True, index=True, nullable=False)
    rtmp_url = Column(String, nullable=False)
    rtsp_port = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "stream_name": self.stream_name,
            "rtmp_url": self.rtmp_url,
            "rtsp_port": self.rtsp_port,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

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

def save_stream(stream_name: str, rtmp_url: str, rtsp_port: int) -> bool:
    """
    Save a stream to the database.

    Args:
        stream_name (str): The name of the stream
        rtmp_url (str): The RTMP URL of the stream
        rtsp_port (int): The RTSP port of the stream

    Returns:
        bool: True if the stream was saved successfully, False otherwise
    """
    db = get_db()
    try:
        stream = Stream(
            stream_name=stream_name,
            rtmp_url=rtmp_url,
            rtsp_port=rtsp_port
        )
        db.add(stream)
        db.commit()
        return True
    except IntegrityError:
        # Stream with this name already exists
        db.rollback()
        return False
    except Exception as e:
        db.rollback()
        print(f"Error saving stream: {e}")
        return False
    finally:
        db.close()

def update_stream(stream_name: str, rtmp_url: str, rtsp_port: int) -> bool:
    """
    Update an existing stream in the database.

    Args:
        stream_name (str): The name of the stream
        rtmp_url (str): The new RTMP URL of the stream
        rtsp_port (int): The new RTSP port of the stream

    Returns:
        bool: True if the stream was updated successfully, False otherwise
    """
    db = get_db()
    try:
        stream = db.query(Stream).filter(Stream.stream_name == stream_name).first()
        if not stream:
            return False

        stream.rtmp_url = rtmp_url
        stream.rtsp_port = rtsp_port
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error updating stream: {e}")
        return False
    finally:
        db.close()

def delete_stream(stream_name: str) -> bool:
    """
    Delete a stream from the database.

    Args:
        stream_name (str): The name of the stream

    Returns:
        bool: True if the stream was deleted successfully, False otherwise
    """
    db = get_db()
    try:
        stream = db.query(Stream).filter(Stream.stream_name == stream_name).first()
        if not stream:
            return False

        db.delete(stream)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Error deleting stream: {e}")
        return False
    finally:
        db.close()

def get_stream(stream_name: str) -> Optional[Dict]:
    """
    Get a stream from the database.

    Args:
        stream_name (str): The name of the stream

    Returns:
        Optional[Dict]: A dictionary containing the stream information, or None if not found
    """
    db = get_db()
    try:
        stream = db.query(Stream).filter(Stream.stream_name == stream_name).first()
        if stream:
            return stream.to_dict()
        return None
    finally:
        db.close()

def get_all_streams() -> List[Dict]:
    """
    Get all streams from the database.

    Returns:
        List[Dict]: A list of dictionaries containing stream information
    """
    db = get_db()
    try:
        streams = db.query(Stream).all()
        return [stream.to_dict() for stream in streams]
    finally:
        db.close()

# Initialize the database when the module is imported
init_db()
