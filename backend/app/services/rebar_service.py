from sqlalchemy.orm import Session

from app import models


def list_development_lengths(db: Session) -> list[models.DevelopmentLength]:
    return db.query(models.DevelopmentLength).order_by(models.DevelopmentLength.id).all()


def list_lap_splice_lengths(db: Session) -> list[models.LapSpliceLength]:
    return db.query(models.LapSpliceLength).order_by(models.LapSpliceLength.id).all()


def get_development_length_by_mark(db: Session, *, bar_mark: str) -> models.DevelopmentLength | None:
    return db.query(models.DevelopmentLength).filter(models.DevelopmentLength.bar_mark == bar_mark).first()


def get_lap_splice_length_by_mark(db: Session, *, bar_mark: str) -> models.LapSpliceLength | None:
    return db.query(models.LapSpliceLength).filter(models.LapSpliceLength.bar_mark == bar_mark).first()
