import logging
from collections import Counter
from typing import Any, Dict, List, TypedDict, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.tools.despiece import (
    BeamDetailPayload,
    BeamPresetResponse,
    DetailingRequest,
    DetailingResponse,
)
from app.schemas.design import (
    DesignCreate,
    DesignRead,
    DespieceVigaCreate,
    DespieceVigaRead,
    DespieceVigaUpdate,
)
from app.services import design_service
from app.services.detailing_service import BeamDetailingService
from app import models

router = APIRouter(prefix="/tools/despiece", tags=["tools: despiece de vigas"])

detailing_service = BeamDetailingService()
logger = logging.getLogger(__name__)


class BarConfig(TypedDict):
    diameter: str
    quantity: int


@router.get("/presets", response_model=BeamPresetResponse)
def get_presets():
    return BeamPresetResponse(
        fc_options=["21 MPa (3000 psi)", "24 MPa (3500 psi)", "28 MPa (4000 psi)", "32 MPa (4600 psi)"],
        fy_options=["420 MPa (Grado 60)", "520 MPa (Grado 75)"],
        hook_options=["90", "135", "180"],
        max_bar_lengths=["6m", "9m", "12m"],
        energy_classes=["DES", "DMO", "DMI"],
        diameter_options=["#3", "#4", "#5", "#6", "#7", "#8", "#9", "#10", "#11", "#14", "#18"],
    )


@router.post("/compute-detailing", response_model=DetailingResponse)
def compute_beam_detailing(
    *,
    request: DetailingRequest,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(deps.get_current_user),
):
    try:
        user_id = _get_user_id(current_user)
        logger.info("Calculando despiece para usuario %s", user_id)
        request_data = request.model_dump(exclude_none=True)
        response = detailing_service.compute_detailing(request_data)

        if response.success:
            background_tasks.add_task(
                log_detailing_computation,
                user_id=user_id,
                request_data=request_data,
                response_data=response.model_dump(),
            )

        return response

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Error en compute_beam_detailing: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al calcular despiece: {exc}",
        ) from exc


@router.post("/designs/{design_id}/compute-detailing", response_model=DetailingResponse)
def compute_detailing_for_design(
    *,
    design_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    try:
        user_id = _get_user_id(current_user)
        design = design_service.get_design(db, design_id=design_id, user_id=user_id)
        if design is None or design.beam_despiece is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Diseño o despiece no encontrado",
            )

        despiece = design.beam_despiece
        logger.info(
            "Calculando despiece para diseño %s (despiece %s)",
            design_id,
            despiece.id,
        )

        request_data = {
            "span_geometries": despiece.span_geometries or [],
            "axis_supports": [
                {"support_width_cm": width, "label": f"EJE {index + 1}"}
                for index, width in enumerate(despiece.support_widths_cm or [])
            ],
            "top_bars_config": _extract_bar_config(despiece.top_bar_diameters or []),
            "bottom_bars_config": _extract_bar_config(despiece.bottom_bar_diameters or []),
            "segment_reinforcements": despiece.segment_reinforcements or [],
            "has_initial_cantilever": despiece.has_cantilevers,
            "has_final_cantilever": despiece.has_cantilevers,
            "cover_cm": despiece.cover_cm,
            "max_rebar_length_m": despiece.max_rebar_length_m,
            "hook_type": despiece.hook_type,
            "energy_dissipation_class": despiece.energy_dissipation_class,
            "concrete_strength": despiece.concrete_strength,
            "reinforcement": despiece.reinforcement,
            "lap_splice_length_min_m": despiece.lap_splice_length_min_m,
        }

        response = detailing_service.compute_detailing(request_data)

        if response.success and response.results:
            despiece.update_detailing(response.model_dump())
            db.add(despiece)
            db.commit()
            db.refresh(despiece)

            background_tasks.add_task(
                log_design_detailing,
                design_id=design_id,
                user_id=user_id,
                response_data=response.model_dump(),
            )

        return response

    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Error en compute_detailing_for_design: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al calcular despiece para diseño: {exc}",
        ) from exc


@router.get("/designs/{design_id}/detailing", response_model=DetailingResponse)
def get_detailing_for_design(
    *,
    design_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = _get_user_id(current_user)
    design = design_service.get_design(db, design_id=design_id, user_id=user_id)
    if design is None or design.beam_despiece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diseño o despiece no encontrado",
        )

    despiece = design.beam_despiece

    if not despiece.detailing_computed or not despiece.detailing_results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El despiece no ha sido calculado aún. Use POST /compute-detailing primero.",
        )

    return DetailingResponse(
        success=True,
        results=despiece.detailing_results,
        message="Despiece recuperado de la base de datos",
        computation_time_ms=None,
    )


@router.get("/designs/{design_id}/detailing/validation")
def get_detailing_validation(
    *,
    design_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = _get_user_id(current_user)
    design = design_service.get_design(db, design_id=design_id, user_id=user_id)
    if design is None or design.beam_despiece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diseño o despiece no encontrado",
        )

    despiece = design.beam_despiece

    if not despiece.detailing_computed:
        return {"computed": False, "message": "Despiece no calculado"}

    return {
        "computed": True,
        "validation_passed": despiece.detailing_results.get("validation_passed", False),
        "warnings": despiece.detailing_warnings or [],
        "warning_count": len(despiece.detailing_warnings or []),
        "optimization_score": despiece.optimization_score,
        "computed_at": despiece.detailing_computed_at.isoformat() if despiece.detailing_computed_at else None,
        "version": despiece.detailing_version,
    }


@router.post("/designs/{design_id}/detailing/recompute")
def recompute_detailing(
    *,
    design_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    return compute_detailing_for_design(
        design_id=design_id,
        background_tasks=background_tasks,
        db=db,
        current_user=current_user,
    )


@router.post("/designs", response_model=DesignRead, status_code=status.HTTP_201_CREATED)
def create_beam_design(
    *,
    payload: BeamDetailPayload,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = _get_user_id(current_user)
    despiece_fields = set(DespieceVigaCreate.model_fields.keys())
    despiece_payload = DespieceVigaCreate(**payload.model_dump(include=despiece_fields))
    settings_data = payload.model_dump(exclude=despiece_fields)

    design_in = DesignCreate(
        title=f"Despiece {payload.beam_label}",
        description=f"Proyecto {payload.project_name}",
        design_type="beam_detailing",
        settings=settings_data,
        despiece_viga=despiece_payload,
    )
    return design_service.create_design(db, design_in=design_in, user_id=user_id)


@router.get("/designs/{design_id}", response_model=DespieceVigaRead)
def get_beam_despiece(
    *,
    design_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = _get_user_id(current_user)
    design = design_service.get_design(db, design_id=design_id, user_id=user_id)
    if design is None or design.beam_despiece is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despiece no encontrado")
    return design.beam_despiece


@router.put("/designs/{design_id}", response_model=DespieceVigaRead)
def update_beam_despiece(
    *,
    design_id: int,
    payload: DespieceVigaUpdate,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    user_id = _get_user_id(current_user)
    updated = design_service.update_despiece_for_design(
        db,
        design_id=design_id,
        user_id=user_id,
        despiece_in=payload,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despiece no encontrado")
    return updated


@router.delete("/designs/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_beam_despiece(
    *,
    design_id: int,
    db: Session = Depends(deps.get_db_session),
    current_user: models.User = Depends(deps.get_current_user),
):
    deleted = design_service.delete_despiece_for_design(
        db,
        design_id=design_id,
        user_id=_get_user_id(current_user),
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Despiece no encontrado")


def _extract_bar_config(diameters: List[str]) -> List[BarConfig]:
    if not diameters:
        return []
    counts = Counter(diameters)
    return [{"diameter": diameter, "quantity": count} for diameter, count in counts.items()]


def _get_user_id(user: models.User) -> int:
    user_id = getattr(user, "id", None)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inválido")
    return cast(int, user_id)


async def log_detailing_computation(user_id: int, request_data: Dict, response_data: Dict):
    logger.info("Despiece calculado para usuario %s", user_id)


async def log_design_detailing(design_id: int, user_id: int, response_data: Dict):
    logger.info("Despiece calculado para diseño %s por usuario %s", design_id, user_id)
