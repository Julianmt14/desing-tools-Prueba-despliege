from typing import cast

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app import models

MAX_PASSWORD_BYTES = 72


def _validate_password_length(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña no puede superar 72 caracteres (limitación de bcrypt)",
        )
    return password


def authenticate_user(db: Session, username: str, password: str) -> models.User | None:
    user = (
        db.query(models.User)
        .filter(or_(models.User.username == username, models.User.email == username))
        .first()
    )
    if not user or not verify_password(password, cast(str, user.hashed_password)):
        return None
    return user


def create_user(db: Session, *, username: str, email: str, password: str) -> models.User:
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario ya existe")
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo ya existe")
    normalized_password = _validate_password_length(password)

    try:
        hashed_password = get_password_hash(normalized_password)
    except ValueError as exc:
        if "password cannot be longer than 72 bytes" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña no puede superar 72 caracteres (limitación de bcrypt)",
            ) from exc
        raise

    user = models.User(
        username=username,
        email=email,
        hashed_password=hashed_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_tokens_for_user(user: models.User) -> tuple[str, str]:
    username = cast(str, user.username)
    access = create_access_token(subject=username)
    refresh = create_refresh_token(subject=username)
    return access, refresh


def refresh_tokens(db: Session, refresh_token: str) -> tuple[str, str]:
    username = decode_refresh_token(refresh_token)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de refresco inválido")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return create_tokens_for_user(user)
