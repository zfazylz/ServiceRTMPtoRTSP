"""
Pydantic models for stream data validation and serialization.
"""

from pydantic import BaseModel, validator, Field


class StreamCreate(BaseModel):
    """
    Модель для создания нового потока.

    Атрибуты:
        rtmp_url: URL RTMP-потока
        stream_name: Уникальное имя для потока
        rtsp_port: Порт для RTSP-сервера (по умолчанию 8554)
    """
    rtmp_url: str = Field(
        ...,
        description="URL RTMP-потока (должен начинаться с rtmp://)",
        example="rtmp://example.com/live/stream",
    )
    stream_name: str = Field(
        ...,
        description="Уникальное имя для потока (без пробелов)",
        example="my_stream",
    )
    rtsp_port: int = Field(
        8554,
        description="Порт для RTSP-сервера (между 1024 и 65535)",
        ge=1024,
        le=65535,
        example=8554,
    )

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

    class Config:
        schema_extra = {
            "example": {
                "rtmp_url": "rtmp://example.com/live/stream",
                "stream_name": "my_stream",
                "rtsp_port": 8554,
            },
        }


class Stream(BaseModel):
    """
    Модель потока с полной информацией.

    Атрибуты:
        name: Имя потока
        rtmp_url: URL RTMP-потока
        rtsp_url: URL RTSP-потока
        rtsp_port: Порт RTSP-сервера
        logs_url: URL для просмотра логов в веб-интерфейсе
        logs_file_url: URL для доступа к файлу логов
        status: Статус потока (активен/неактивен)
        status_reason: Причина текущего статуса
    """
    name: str = Field(
        ...,
        description="Уникальное имя потока",
    )
    rtmp_url: str = Field(
        ...,
        description="URL RTMP-потока",
    )
    rtsp_url: str = Field(
        ...,
        description="URL RTSP-потока для доступа к конвертированному потоку",
    )
    rtsp_port: int = Field(
        ...,
        description="Порт RTSP-сервера",
    )
    logs_url: str = Field(
        ...,
        description="URL для просмотра логов в веб-интерфейсе",
    )
    logs_file_url: str = Field(
        ...,
        description="URL для доступа к файлу логов",
    )
    status: bool = Field(
        ...,
        description="Статус потока (true - активен, false - неактивен)",
    )
    status_reason: str = Field(
        ...,
        description="Причина текущего статуса",
    )

    class Config:
        schema_extra = {
            "example": {
                "name": "my_stream",
                "rtmp_url": "rtmp://example.com/live/stream",
                "rtsp_url": "rtsp://localhost:8554/my_stream",
                "rtsp_port": 8554,
                "logs_url": "/logs/my_stream",
                "logs_file_url": "/static/logs/my_stream.log",
                "status": True,
                "status_reason": "Stream is running normally",
            },
        }
