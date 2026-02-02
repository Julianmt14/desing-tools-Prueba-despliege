from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.modules.drawing.schemas.drawing import DrawingExportRequest


class DrawingExportJobCreate(DrawingExportRequest):
    """Payload para solicitar una exportación asíncrona."""


class DrawingExportJobRead(BaseModel):
    job_id: str
    design_id: int
    format: str
    template: str
    scale: float
    locale: Literal["es-CO", "en-US"]
    include_preview: bool = False
    status: Literal["queued", "processing", "completed", "failed"]
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    file_path: Optional[str] = None
    preview_path: Optional[str] = None
    expires_at: Optional[datetime] = None
    message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


__all__ = ["DrawingExportJobCreate", "DrawingExportJobRead"]
