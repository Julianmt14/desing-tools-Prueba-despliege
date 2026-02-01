from datetime import datetime, timedelta
from types import SimpleNamespace

import bcrypt
from jose import jwt, JWTError
from passlib.context import CryptContext

# Algunas versiones de bcrypt eliminan el atributo __about__ requerido por Passlib.
# Para mantener compatibilidad, inyectamos un contenedor mínimo cuando falte.
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = SimpleNamespace(__version__=getattr(bcrypt, "__version__", "unknown"))

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def _create_token(subject: str, expires_minutes: int, token_type: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode = {"exp": expire, "sub": subject, "type": token_type}
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    minutes = expires_minutes or settings.access_token_expire_minutes
    return _create_token(subject, minutes, "access")


def create_refresh_token(subject: str, expires_minutes: int | None = None) -> str:
    minutes = expires_minutes or settings.refresh_token_expire_minutes
    return _create_token(subject, minutes, "refresh")


def _decode_token(token: str, expected_type: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None


def decode_access_token(token: str) -> str | None:
    return _decode_token(token, "access")


def decode_refresh_token(token: str) -> str | None:
    return _decode_token(token, "refresh")
