from sqlalchemy import Column, DateTime, Integer, Numeric, String, func

from app.core.database import Base


class HookLength(Base):
    __tablename__ = "hook_lengths"

    id = Column(Integer, primary_key=True, index=True)
    bar_mark = Column(String(10), nullable=False, unique=True)
    longitudinal_90_m = Column(Numeric(5, 3), nullable=False)
    longitudinal_180_m = Column(Numeric(5, 3), nullable=False)
    stirrup_135_m = Column(Numeric(5, 3), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
