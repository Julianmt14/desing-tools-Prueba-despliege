from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.api import deps
from app.schemas.drawing_export import DrawingExportJobCreate, DrawingExportJobRead
from app.services import design_service, drawing_export_service

router = APIRouter(prefix="/drawing/exports", tags=["drawing-exports"])


@router.post("/", response_model=DrawingExportJobRead, status_code=status.HTTP_202_ACCEPTED)
def enqueue_drawing_export(
    *,
    export_in: DrawingExportJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    design = design_service.get_design(
        db,
        design_id=export_in.design_id,
        user_id=int(current_user.id),
    )
    if design is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el diseño solicitado.")

    request = export_in.model_copy(update={"locale": drawing_export_service.coerce_locale(export_in.locale)})
    job = drawing_export_service.create_export_job(
        db,
        design=design,
        request=request,
        user_id=int(current_user.id),
    )
    background_tasks.add_task(drawing_export_service.process_export_job, job.job_id)
    return drawing_export_service.serialize_export_job(job)


@router.get("/{job_id}", response_model=DrawingExportJobRead)
def get_export_job(
    *,
    job_id: str,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    job = drawing_export_service.get_job_for_user(
        db,
        job_id=job_id,
        user_id=int(current_user.id),
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el job solicitado.")

    return drawing_export_service.serialize_export_job(job)
