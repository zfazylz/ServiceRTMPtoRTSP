"""
API endpoints for stream management.
"""

from typing import List

from fastapi import APIRouter, Request, HTTPException

from app.models.stream import StreamCreate, Stream

# Create a router for stream endpoints
router = APIRouter(
    prefix="/api/streams",
    tags=["streams"],
    responses={404: {"description": "Stream not found"}},
)


# We'll import stream_manager inside the functions to avoid circular imports


@router.get(
    "", response_model=List[Stream],
    summary="Получить все потоки",
    description="Возвращает список всех активных потоков с их статусами и URL",
)
async def get_streams(request: Request):
    """
    Получает список всех активных потоков.

    Возвращает полную информацию о каждом потоке, включая:
    - Имя потока
    - URL RTMP
    - URL RTSP
    - Порт RTSP
    - URL логов
    - Статус потока
    - Причину статуса
    """
    from app import stream_manager
    return stream_manager.get_all_streams(host=request.url.hostname)


@router.get(
    "/{stream_name}", response_model=Stream,
    summary="Получить информацию о конкретном потоке",
    description="Возвращает детальную информацию о потоке по его имени",
)
async def get_stream(
        stream_name: str,
        request: Request,
):
    """
    Получает информацию о конкретном потоке по его имени.

    Параметры:
    - **stream_name**: Уникальное имя потока

    Возвращает полную информацию о потоке, включая:
    - Имя потока
    - URL RTMP
    - URL RTSP
    - Порт RTSP
    - URL логов
    - Статус потока
    - Причину статуса

    Если поток не найден, возвращает ошибку 404.
    """
    from app import stream_manager
    stream = stream_manager.get_stream(stream_name, host=request.url.hostname)
    if not stream:
        raise HTTPException(status_code=404, detail=f"Поток '{stream_name}' не найден")
    return stream


@router.post(
    "", response_model=Stream,
    summary="Создать новый поток",
    description="Создает новый поток конвертации RTMP в RTSP",
    status_code=201,
)
async def create_stream(
        stream: StreamCreate,
        request: Request,
):
    """
    Создает новый поток конвертации RTMP в RTSP.

    Принимает:
    - **rtmp_url**: URL RTMP-потока (должен начинаться с rtmp://)
    - **stream_name**: Уникальное имя для потока (без пробелов)
    - **rtsp_port**: Порт для RTSP-сервера (по умолчанию 8554)

    Возвращает полную информацию о созданном потоке.

    Если поток с таким именем уже существует или произошла ошибка при запуске конвертера,
    возвращает ошибку 400.
    """
    from app import stream_manager
    success = stream_manager.add_stream(
        rtmp_url=stream.rtmp_url,
        rtsp_port=stream.rtsp_port,
        stream_name=stream.stream_name,
        host=request.url.hostname,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Не удалось добавить поток '{stream.stream_name}'. "
                f"Возможно, он уже существует или произошла ошибка при запуске конвертера."
            ),
        )

    return stream_manager.get_stream(stream.stream_name, host=request.url.hostname)


@router.delete(
    "/{stream_name}",
    summary="Удалить поток",
    description="Удаляет поток конвертации по его имени",
)
async def remove_stream(
        stream_name: str,
):
    """
    Удаляет поток конвертации по его имени.

    Параметры:
    - **stream_name**: Уникальное имя потока для удаления

    Возвращает сообщение об успешном удалении.

    Если поток не найден, возвращает ошибку 404.
    """
    from app import stream_manager
    success = stream_manager.remove_stream(stream_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Поток '{stream_name}' не найден")
    return {"message": f"Поток '{stream_name}' успешно удален"}


@router.post(
    "/{stream_name}/clear-error",
    summary="Сбросить ошибку потока",
    description="Сбрасывает состояние ошибки для указанного потока",
)
async def clear_stream_error(
        stream_name: str,
):
    """
    Сбрасывает состояние ошибки для указанного потока.

    Это полезно, если поток находится в состоянии ошибки, но проблема была устранена.
    После сброса ошибки поток будет считаться работающим, если не возникнут новые ошибки.

    Параметры:
    - **stream_name**: Уникальное имя потока для сброса ошибки

    Возвращает сообщение об успешном сбросе ошибки.

    Если поток не найден, возвращает ошибку 404.
    """
    from app import stream_manager
    success = stream_manager.clear_stream_error(stream_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Поток '{stream_name}' не найден")
    return {"message": f"Ошибка потока '{stream_name}' успешно сброшена"}
