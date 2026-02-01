from sqlalchemy.orm import Session

from app import models


def list_hook_lengths(db: Session) -> list[models.HookLength]:
    return db.query(models.HookLength).order_by(models.HookLength.id).all()


def get_hook_length_by_mark(db: Session, *, bar_mark: str) -> models.HookLength | None:
    return db.query(models.HookLength).filter(models.HookLength.bar_mark == bar_mark).first()
