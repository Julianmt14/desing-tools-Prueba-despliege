from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Design(Base):
    __tablename__ = "designs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(500))
    design_type = Column(String(50), nullable=False)
    settings = Column(JSON, nullable=False, default={})
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    thumbnail_url = Column(String(500))

    user = relationship("User", backref="designs")
    beam_despiece = relationship(
        "DespieceViga",
        back_populates="design",
        uselist=False,
        cascade="all, delete-orphan",
    )


class DespieceViga(Base):
    __tablename__ = "despiece_vigas"

    id = Column(Integer, primary_key=True, index=True)
    design_id = Column(
        Integer,
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    project_name = Column(String(255), nullable=False)
    beam_label = Column(String(255), nullable=False)
    top_bars_qty = Column(Integer, nullable=False)
    bottom_bars_qty = Column(Integer, nullable=False)
    top_bar_diameters = Column(JSON, nullable=True)
    bottom_bar_diameters = Column(JSON, nullable=True)
    max_rebar_length_m = Column(String(10), nullable=False)
    lap_splice_length_min_m = Column(Float, nullable=False)
    lap_splice_location = Column(String(255), nullable=False)
    beam_total_length_m = Column(Float, nullable=False, default=0)
    section_changes = Column(JSON, nullable=True)
    has_cantilevers = Column(Boolean, nullable=False, default=False)
    hook_type = Column(String(20), nullable=False)
    cover_cm = Column(Integer, nullable=False, default=4)
    span_count = Column(Integer, nullable=False, default=1)
    support_widths_cm = Column(JSON, nullable=True)
    span_geometries = Column(JSON, nullable=False, default=list)
    axis_numbering = Column(String(100), nullable=True)
    element_identifier = Column(String(100), nullable=False)
    element_level = Column(Numeric(6, 2), nullable=True)
    element_quantity = Column(Integer, nullable=False, default=1)
    reinforcement = Column(String(100), nullable=False)
    stirrups_config = Column(JSON, nullable=True)
    energy_dissipation_class = Column(String(3), nullable=False)
    concrete_strength = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    design = relationship("Design", back_populates="beam_despiece")
