from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.hook import HookLengthRead
from app.services import hook_service

router = APIRouter(prefix="/tools/hooks", tags=["tools: ganchos"])


@router.get("/", response_model=list[HookLengthRead])
def list_hook_lengths(db: Session = Depends(deps.get_db_session)):
    return hook_service.list_hook_lengths(db)


@router.get("/{bar_mark}", response_model=HookLengthRead)
def get_hook_length(bar_mark: str, db: Session = Depends(deps.get_db_session)):
    normalized_mark = bar_mark if bar_mark.startswith("#") else f"#{bar_mark}"
    hook = hook_service.get_hook_length_by_mark(db, bar_mark=normalized_mark)
    if hook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gancho no encontrado")
    return hook
