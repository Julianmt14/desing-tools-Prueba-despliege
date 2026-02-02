from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

from sqlalchemy.orm import Session, selectinload

from app import models
from app.core.database import SessionLocal
from app.modules.drawing import BeamDrawingService
from app.modules.drawing.domain import DrawingDocument
from app.modules.drawing.dwg_exporter import DWGExporter
from app.modules.drawing.pdf_exporter import PDFExporter
from app.modules.drawing.preview_renderer import render_svg
from app.modules.drawing.schemas.drawing import BeamDrawingPayload, DrawingExportRequest
from app.services import design_service

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

DOWNLOAD_ROOT = Path.home() / "Downloads" / "Despieces"
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
_RETENTION_DAYS = 14
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_-]+")


@dataclass(slots=True)
class ExportFileResult:
    file_path: Path
    preview_path: Path | None = None
    inline_preview: str | None = None


def coerce_locale(locale: str | None) -> Literal["es-CO", "en-US"]:
    return "en-US" if locale == "en-US" else "es-CO"


def prepare_destination_dir(project_name: str | None) -> Path:
    folder_name = _slugify(project_name or "Proyecto")
    destination = DOWNLOAD_ROOT / folder_name
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def build_export_filename(beam_label: str | None, draw_format: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(beam_label or "viga")
    extension = _format_extension(draw_format)
    return f"{slug}_{timestamp}.{extension}"


def generate_export_for_design(
    design: models.Design,
    request: DrawingExportRequest,
) -> ExportFileResult:
    payload = design_service.build_beam_drawing_payload(design)
    document = _render_document(payload, request)
    destination_dir = prepare_destination_dir(payload.metadata.project_name)
    filename = build_export_filename(payload.metadata.beam_label, request.format)
    file_path = _save_document_to_disk(document, request, destination_dir, filename)
    preview_path: Path | None = None
    inline_preview: str | None = None

    if request.include_preview:
        if request.format == "svg":
            preview_path = file_path
            inline_preview = _safe_read(preview_path)
        else:
            preview_name = Path(filename).with_suffix(".svg").name
            preview_path = destination_dir / preview_name
            preview_path.write_text(render_svg(document), encoding="utf-8")

    return ExportFileResult(file_path=file_path, preview_path=preview_path, inline_preview=inline_preview)


def create_export_job(
    db: Session,
    *,
    design: models.Design,
    request: DrawingExportRequest,
    user_id: int,
) -> models.DesignExport:
    job = models.DesignExport(
        job_id=str(uuid.uuid4()),
        design_id=design.id,
        user_id=user_id,
        template=request.template,
        format=request.format,
        scale=request.scale,
        locale=request.locale,
        include_preview=request.include_preview,
        status="queued",
        expires_at=datetime.now(timezone.utc) + timedelta(days=_RETENTION_DAYS),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_for_user(db: Session, *, job_id: str, user_id: int) -> models.DesignExport | None:
    return (
        db.query(models.DesignExport)
        .options(selectinload(models.DesignExport.design))
        .filter(models.DesignExport.job_id == job_id, models.DesignExport.user_id == user_id)
        .first()
    )


def serialize_export_job(job: models.DesignExport) -> dict:
    return {
        "job_id": job.job_id,
        "design_id": job.design_id,
        "format": job.format,
        "template": job.template,
        "scale": job.scale,
        "locale": job.locale,
        "include_preview": job.include_preview,
        "status": job.status,
        "file_path": job.file_path,
        "preview_path": job.preview_path,
        "download_url": _path_to_url(job.file_path),
        "preview_url": _path_to_url(job.preview_path),
        "expires_at": job.expires_at,
        "message": job.message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def process_export_job(job_id: str) -> None:
    db = SessionLocal()
    job: Optional[models.DesignExport] = None
    try:
        job = (
            db.query(models.DesignExport)
            .options(selectinload(models.DesignExport.design).selectinload(models.Design.beam_despiece))
            .filter(models.DesignExport.job_id == job_id)
            .first()
        )
        if job is None:
            logger.warning("No se encontró el job de exportación %s", job_id)
            return

        job.status = "processing"
        job.message = None
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)

        design = job.design
        if design is None:
            raise RuntimeError("El diseño asociado a la exportación ya no existe")

        request = DrawingExportRequest(
            design_id=job.design_id,
            format=job.format,
            template=job.template,
            scale=job.scale,
            locale=job.locale,
            include_preview=job.include_preview,
        )
        result = generate_export_for_design(design, request)
        job.file_path = str(result.file_path)
        job.preview_path = str(result.preview_path) if result.preview_path else None
        job.status = "completed"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # pragma: no cover - fallbacks de runtime
        logger.exception("Falló el job de exportación %s", job_id)
        db.rollback()
        if job is not None:
            job.status = "failed"
            job.message = str(exc)
            job.updated_at = datetime.now(timezone.utc)
            db.add(job)
            db.commit()
    finally:
        db.close()


def _render_document(payload: BeamDrawingPayload, request: DrawingExportRequest) -> DrawingDocument:
    service = BeamDrawingService(template_key=request.template)
    return service.render_document(payload, export_request=request)


def _save_document_to_disk(
    document: DrawingDocument,
    request: DrawingExportRequest,
    destination_dir: Path,
    filename: str,
) -> Path:
    if request.format in {"dwg", "dxf"}:
        exporter = DWGExporter()
        return exporter.export(document, filename=filename, output_dir=destination_dir)

    if request.format == "pdf":
        exporter = PDFExporter()
        target_path = destination_dir / filename
        return exporter.export(document, target_path)

    if request.format == "svg":
        target_path = destination_dir / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(render_svg(document), encoding="utf-8")
        return target_path

    raise RuntimeError(f"Formato no soportado: {request.format}")


def _path_to_url(path_str: str | None) -> str | None:
    if not path_str:
        return None
    path = Path(path_str)
    try:
        return path.resolve().as_uri()
    except OSError:
        return None


def _format_extension(draw_format: str) -> str:
    mapping = {
        "dwg": "dwg",
        "dxf": "dxf",
        "pdf": "pdf",
        "svg": "svg",
    }
    return mapping.get(draw_format, "dwg")


def _slugify(value: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", value.strip()) if value else ""
    cleaned = cleaned.strip("_")
    return cleaned or "archivo"


def _safe_read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


__all__ = [
    "ExportFileResult",
    "DOWNLOAD_ROOT",
    "build_export_filename",
    "coerce_locale",
    "create_export_job",
    "generate_export_for_design",
    "get_job_for_user",
    "prepare_destination_dir",
    "process_export_job",
    "serialize_export_job",
]
