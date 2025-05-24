"""
CRUD operations for the database.

This module provides functions for creating, reading, updating, and deleting
stream information in the database.
"""

from typing import List, Dict, Optional

from sqlalchemy.exc import IntegrityError

from app.database.models import Stream
from app.database.session import get_db


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
            rtsp_port=rtsp_port,
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
