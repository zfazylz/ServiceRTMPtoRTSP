"""
RTMP to RTSP Converter Web Application

A FastAPI web application for converting RTMP streams to RTSP streams.
"""

import os
import logging
import io
from typing import Optional, List, Dict
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, validator

from app.converter import StreamManager

# Create necessary directories
static_dir = os.path.join(os.getcwd(), 'app/static')
logs_dir = os.path.join(static_dir, 'logs')

if not os.path.exists(static_dir):
    os.makedirs(static_dir)

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Конвертер RTMP в RTSP",
    description="Веб-приложение для конвертации RTMP-потоков в RTSP-потоки",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# Create a global StreamManager instance
stream_manager = StreamManager()

# Define Pydantic models for API
class StreamCreate(BaseModel):
    rtmp_url: str
    stream_name: str
    rtsp_port: int = 8554

    @validator('rtmp_url')
    def validate_rtmp_url(cls, v):
        if not v.startswith('rtmp://'):
            raise ValueError('URL RTMP должен начинаться с rtmp://')
        return v

    @validator('stream_name')
    def validate_stream_name(cls, v):
        if not v or ' ' in v:
            raise ValueError('Имя потока не может быть пустым или содержать пробелы')
        return v

    @validator('rtsp_port')
    def validate_rtsp_port(cls, v):
        if v < 1024 or v > 65535:
            raise ValueError('Порт RTSP должен быть между 1024 и 65535')
        return v

class Stream(BaseModel):
    name: str
    rtmp_url: str
    rtsp_url: str
    rtsp_port: int
    logs_url: str
    logs_file_url: str
    status: bool
    status_reason: str

# Define API endpoints
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    streams = stream_manager.get_all_streams(host=request.url.hostname)
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "streams": streams}
    )

@app.get("/add", response_class=HTMLResponse)
async def add_stream_form(request: Request):
    """Render the add stream form."""
    return templates.TemplateResponse(
        "add_stream.html", 
        {"request": request}
    )

@app.post("/add")
async def add_stream(
    request: Request,
    rtmp_url: str = Form(...),
    stream_name: str = Form(...),
    rtsp_port: int = Form(8554)
):
    """Add a new stream."""
    try:
        # Validate input using Pydantic model
        stream_data = StreamCreate(
            rtmp_url=rtmp_url,
            stream_name=stream_name,
            rtsp_port=rtsp_port
        )

        # Add the stream
        success = stream_manager.add_stream(
            rtmp_url=stream_data.rtmp_url,
            rtsp_port=stream_data.rtsp_port,
            stream_name=stream_data.stream_name,
            host=request.url.hostname
        )

        if not success:
            return templates.TemplateResponse(
                "add_stream.html",
                {
                    "request": request,
                    "error": f"Не удалось добавить поток '{stream_data.stream_name}'. Возможно, он уже существует или произошла ошибка при запуске конвертера."
                }
            )

        # Redirect to home page
        return RedirectResponse(url="/", status_code=303)
    except ValueError as e:
        # Handle validation errors
        return templates.TemplateResponse(
            "add_stream.html",
            {"request": request, "error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error adding stream: {str(e)}")
        return templates.TemplateResponse(
            "add_stream.html",
            {"request": request, "error": f"Произошла непредвиденная ошибка: {str(e)}"}
        )

@app.post("/delete/{stream_name}")
async def delete_stream(stream_name: str):
    """Delete a stream."""
    success = stream_manager.remove_stream(stream_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Поток '{stream_name}' не найден")
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/streams", response_model=List[Stream])
async def get_streams(request: Request):
    """Get all streams (API endpoint)."""
    return stream_manager.get_all_streams(host=request.url.hostname)

@app.get("/api/streams/{stream_name}", response_model=Stream)
async def get_stream(stream_name: str, request: Request):
    """Get a specific stream (API endpoint)."""
    stream = stream_manager.get_stream(stream_name, host=request.url.hostname)
    if not stream:
        raise HTTPException(status_code=404, detail=f"Поток '{stream_name}' не найден")
    return stream

@app.get("/logs/{stream_name}", response_class=HTMLResponse)
async def view_stream_logs(stream_name: str, request: Request):
    """View logs for a specific stream."""
    stream = stream_manager.get_stream(stream_name, host=request.url.hostname)
    if stream is None:
        raise HTTPException(status_code=404, detail=f"Поток '{stream_name}' не найден")
    return templates.TemplateResponse(
        "stream_logs.html",
        {"request": request, "stream_name": stream_name, "logs_file_url": stream["logs_file_url"]}
    )

@app.post("/api/streams", response_model=Stream)
async def create_stream(stream: StreamCreate, request: Request):
    """Create a new stream (API endpoint)."""
    success = stream_manager.add_stream(
        rtmp_url=stream.rtmp_url,
        rtsp_port=stream.rtsp_port,
        stream_name=stream.stream_name,
        host=request.url.hostname
    )

    if not success:
        raise HTTPException(
            status_code=400, 
            detail=f"Не удалось добавить поток '{stream.stream_name}'. Возможно, он уже существует или произошла ошибка при запуске конвертера."
        )

    return stream_manager.get_stream(stream.stream_name, host=request.url.hostname)

@app.delete("/api/streams/{stream_name}")
async def remove_stream(stream_name: str):
    """Remove a stream (API endpoint)."""
    success = stream_manager.remove_stream(stream_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Поток '{stream_name}' не найден")
    return {"message": f"Поток '{stream_name}' успешно удален"}

# Startup event handler
@app.on_event("startup")
def startup_event():
    """Load and start streams from the database when the application starts."""
    logger.info("Application starting up, loading streams from database...")
    count = stream_manager.load_streams_from_db(host="localhost")
    logger.info(f"Loaded and started {count} streams from database")

# Shutdown event handler
@app.on_event("shutdown")
def shutdown_event():
    """Stop all streams when the application shuts down."""
    logger.info("Application shutting down, stopping all streams...")
    stream_manager.stop_all_streams()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
