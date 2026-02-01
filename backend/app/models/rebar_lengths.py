from sqlalchemy import Column, DateTime, Integer, Numeric, String, func

from app.core.database import Base


class DevelopmentLength(Base):
    __tablename__ = "development_lengths"

    id = Column(Integer, primary_key=True, index=True)
    bar_mark = Column(String(10), nullable=False, unique=True)
    fc_21_mpa_m = Column(Numeric(5, 2), nullable=False)
    fc_24_mpa_m = Column(Numeric(5, 2), nullable=False)
    fc_28_mpa_m = Column(Numeric(5, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LapSpliceLength(Base):
    __tablename__ = "lap_splice_lengths"

    id = Column(Integer, primary_key=True, index=True)
    bar_mark = Column(String(10), nullable=False, unique=True)
    fc_21_mpa_m = Column(Numeric(5, 2), nullable=False)
    fc_24_mpa_m = Column(Numeric(5, 2), nullable=False)
    fc_28_mpa_m = Column(Numeric(5, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
