from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.modules.drawing import BeamDrawingService
from app.modules.drawing.drawing_service import serialize_document
from app.schemas.design import DesignCreate, DesignRead
from app.modules.drawing.templates import list_templates
from app.modules.drawing.schemas import BeamDrawingPayload
from app.services import design_service
from app import models

router = APIRouter(prefix="/designs", tags=["designs"])


@router.get("/", response_model=list[DesignRead])
def list_designs(
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    return design_service.list_designs(db, user_id=user_id)


@router.post("/", response_model=DesignRead, status_code=status.HTTP_201_CREATED)
def create_design(
    *,
    design_in: DesignCreate,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    return design_service.create_design(db, design_in=design_in, user_id=user_id)


@router.get("/drawing-templates")
def list_drawing_templates():
    return list_templates()

@router.get("/{design_id}/drawing-payload", response_model=BeamDrawingPayload)
def get_design_drawing_payload(
    *,
    design_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    design = design_service.get_design(db, design_id=design_id, user_id=user_id)
    if design is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el diseño solicitado.",
        )

    try:
        return design_service.build_beam_drawing_payload(design)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{design_id}/drawing-document")
def get_design_drawing_document(
    *,
    design_id: int,
    template: str | None = None,
    locale: str | None = None,
    scale: float | None = None,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = cast(int, current_user.id)
    design = design_service.get_design(db, design_id=design_id, user_id=user_id)
    if design is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el diseño solicitado.",
        )

    try:
        payload = design_service.build_beam_drawing_payload(design)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    service = BeamDrawingService(template_key=template)
    request = None
    if template or locale or scale:
        from app.modules.drawing.schemas import DrawingExportRequest

        locale_value = locale if locale in {"es-CO", "en-US"} else "es-CO"
        locale_literal = "en-US" if locale_value == "en-US" else "es-CO"
        request = DrawingExportRequest(
            design_id=design_id,
            template=template or "beam/default",
            locale=locale_literal,
            scale=scale or 50.0,
        )
    document = service.render_document(
        payload,
        template_override=template,
        locale=locale,
        export_request=request,
    )
    return serialize_document(document)
