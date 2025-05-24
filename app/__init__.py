"""
RTMP to RTSP Converter Web Application

A FastAPI web application for converting RTMP streams to RTSP streams.
"""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import streams_router
from app.config import logger
from app.converter import StreamManager
from app.web import web_router

# Initialize FastAPI app
app = FastAPI(
    title="Конвертер RTMP в RTSP",
    description="Веб-приложение для конвертации RTMP-потоков в RTSP-потоки",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {
            "name": "streams",
            "description": "Операции с потоками: получение, создание, удаление",
        },
    ],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(web_router)
app.include_router(streams_router)

# Create a global StreamManager instance
stream_manager = StreamManager()


# Startup event handler
@app.on_event("startup")
def startup_event():
    """Load and start streams from the database when the application starts."""
    logger.info("Application starting up, loading streams from database...")
    # Use the hostname from environment or default to a value that works in Docker
    hostname = os.environ.get("HOSTNAME", "localhost")
    count = stream_manager.load_streams_from_db(host=hostname)
    logger.info(f"Loaded and started {count} streams from database")


# Shutdown event handler
@app.on_event("shutdown")
def shutdown_event():
    """Stop all streams when the application shuts down."""
    logger.info("Application shutting down, stopping all streams...")
    stream_manager.stop_all_streams()


__all__ = ['app', 'StreamManager']
