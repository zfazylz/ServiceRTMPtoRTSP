"""
Web UI routes for the application.
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models.stream import StreamCreate

# Create a router for web UI routes
router = APIRouter()

# Set up templates
templates = Jinja2Templates(directory="app/templates")


# We'll import stream_manager inside the functions to avoid circular imports


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    from app import stream_manager
    streams = stream_manager.get_all_streams(host=request.url.hostname)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "streams": streams},
    )


@router.get("/add", response_class=HTMLResponse)
async def add_stream_form(request: Request):
    """Render the add stream form."""
    return templates.TemplateResponse(
        "add_stream.html",
        {"request": request},
    )


@router.post("/add")
async def add_stream(
        request: Request,
        rtmp_url: str = Form(...),
        stream_name: str = Form(...),
        rtsp_port: int = Form(8554),
):
    """Add a new stream."""
    try:
        # Validate input using Pydantic model
        stream_data = StreamCreate(
            rtmp_url=rtmp_url,
            stream_name=stream_name,
            rtsp_port=rtsp_port,
        )

        # Add the stream
        from app import stream_manager
        success = stream_manager.add_stream(
            rtmp_url=stream_data.rtmp_url,
            rtsp_port=stream_data.rtsp_port,
            stream_name=stream_data.stream_name,
            host=request.url.hostname,
        )

        if not success:
            return templates.TemplateResponse(
                "add_stream.html",
                {
                    "request": request,
                    "error": (
                        f"Не удалось добавить поток '{stream_data.stream_name}'. "
                        f"Возможно, он уже существует или произошла ошибка при запуске конвертера."
                    ),
                },
            )

        # Redirect to home page
        return RedirectResponse(url="/", status_code=303)
    except ValueError as e:
        # Handle validation errors
        return templates.TemplateResponse(
            "add_stream.html",
            {"request": request, "error": str(e)},
        )
    except Exception as e:
        return templates.TemplateResponse(
            "add_stream.html",
            {
                "request": request,
                "error": f"Произошла непредвиденная ошибка: {str(e)}",
            },
        )


@router.post("/delete/{stream_name}")
async def delete_stream(stream_name: str):
    """Delete a stream."""
    from app import stream_manager
    success = stream_manager.remove_stream(stream_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Поток '{stream_name}' не найден")
    return RedirectResponse(url="/", status_code=303)


@router.get("/logs/{stream_name}", response_class=HTMLResponse)
async def view_stream_logs(stream_name: str, request: Request):
    """View logs for a specific stream."""
    from app import stream_manager
    stream = stream_manager.get_stream(stream_name, host=request.url.hostname)
    if stream is None:
        raise HTTPException(status_code=404, detail=f"Поток '{stream_name}' не найден")
    return templates.TemplateResponse(
        "stream_logs.html",
        {"request": request, "stream_name": stream_name, "logs_file_url": stream["logs_file_url"]},
    )
