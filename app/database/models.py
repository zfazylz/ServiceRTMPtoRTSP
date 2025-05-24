"""
SQLAlchemy models for the database.

This module defines the SQLAlchemy ORM models used in the application.
"""

import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

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

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "stream_name": self.stream_name,
            "rtmp_url": self.rtmp_url,
            "rtsp_port": self.rtsp_port,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
