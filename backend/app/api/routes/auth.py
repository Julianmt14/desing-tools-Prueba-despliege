from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.user import UserCreate, UserRead
from app.schemas.auth import Token, TokenRefreshRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(*, user_in: UserCreate, db: Session = Depends(deps.get_db_session)):
    user = auth_service.create_user(
        db,
        username=user_in.username,
        email=user_in.email,
        password=user_in.password,
    )
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(deps.get_db_session)):
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    access_token, refresh_token = auth_service.create_tokens_for_user(user)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh_access_token(*, payload: TokenRefreshRequest, db: Session = Depends(deps.get_db_session)):
    access_token, refresh_token = auth_service.refresh_tokens(db, payload.refresh_token)
    return Token(access_token=access_token, refresh_token=refresh_token)
