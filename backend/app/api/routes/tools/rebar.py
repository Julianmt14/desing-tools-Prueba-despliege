from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.rebar import RebarLengthRead
from app.services import rebar_service

router = APIRouter(prefix="/tools/rebar", tags=["tools: longitudes de refuerzo"])


def _normalize_mark(bar_mark: str) -> str:
    return bar_mark if bar_mark.startswith("#") else f"#{bar_mark}"


@router.get("/development-lengths", response_model=list[RebarLengthRead])
def list_development_lengths(db: Session = Depends(deps.get_db_session)):
    return rebar_service.list_development_lengths(db)


@router.get("/development-lengths/{bar_mark}", response_model=RebarLengthRead)
def get_development_length(bar_mark: str, db: Session = Depends(deps.get_db_session)):
    mark = _normalize_mark(bar_mark)
    length = rebar_service.get_development_length_by_mark(db, bar_mark=mark)
    if length is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Longitud de desarrollo no encontrada")
    return length


@router.get("/lap-splice-lengths", response_model=list[RebarLengthRead])
def list_lap_splice_lengths(db: Session = Depends(deps.get_db_session)):
    return rebar_service.list_lap_splice_lengths(db)


@router.get("/lap-splice-lengths/{bar_mark}", response_model=RebarLengthRead)
def get_lap_splice_length(bar_mark: str, db: Session = Depends(deps.get_db_session)):
    mark = _normalize_mark(bar_mark)
    length = rebar_service.get_lap_splice_length_by_mark(db, bar_mark=mark)
    if length is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Longitud de traslapo no encontrada")
    return length
