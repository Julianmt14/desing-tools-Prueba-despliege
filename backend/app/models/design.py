from typing import Dict

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

    # Datos básicos del proyecto
    project_name = Column(String(255), nullable=False)
    beam_label = Column(String(255), nullable=False)
    element_identifier = Column(String(100), nullable=False)
    element_level = Column(Numeric(6, 2), nullable=True)
    element_quantity = Column(Integer, nullable=False, default=1)

    # Geometría
    span_count = Column(Integer, nullable=False, default=1)
    beam_total_length_m = Column(Float, nullable=False, default=0)
    has_cantilevers = Column(Boolean, nullable=False, default=False)
    span_geometries = Column(JSON, nullable=False, default=list)
    support_widths_cm = Column(JSON, nullable=True)
    axis_numbering = Column(String(100), nullable=True)
    section_changes = Column(JSON, nullable=True)

    # Refuerzo longitudinal básico
    top_bars_qty = Column(Integer, nullable=False)
    bottom_bars_qty = Column(Integer, nullable=False)
    top_bar_diameters = Column(JSON, nullable=True)
    bottom_bar_diameters = Column(JSON, nullable=True)

    # Refuerzo adicional
    segment_reinforcements = Column(JSON, nullable=True)
    stirrups_config = Column(JSON, nullable=True)

    # Parámetros de diseño
    max_rebar_length_m = Column(String(10), nullable=False)
    lap_splice_length_min_m = Column(Float, nullable=False)
    lap_splice_location = Column(String(255), nullable=False)
    hook_type = Column(String(20), nullable=False)
    cover_cm = Column(Integer, nullable=False, default=4)

    # Materiales
    reinforcement = Column(String(100), nullable=False)
    concrete_strength = Column(String(50), nullable=False)
    energy_dissipation_class = Column(String(3), nullable=False)

    # Notas
    notes = Column(Text, nullable=True)

    # ===== NUEVOS CAMPOS PARA DESPIECE AUTOMÁTICO =====
    detailing_computed = Column(Boolean, nullable=False, default=False)
    detailing_results = Column(JSON, nullable=True)
    detailing_warnings = Column(JSON, nullable=True)
    bar_detailing = Column(JSON, nullable=True)
    prohibited_zones = Column(JSON, nullable=True)
    material_list = Column(JSON, nullable=True)

    # Métricas de optimización
    total_bars_count = Column(Integer, nullable=True)
    total_rebar_weight_kg = Column(Float, nullable=True)
    waste_percentage = Column(Float, nullable=True)
    optimization_score = Column(Float, nullable=True)

    # Control de versiones
    detailing_version = Column(String(20), nullable=True, default="1.0")
    detailing_computed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    design = relationship("Design", back_populates="beam_despiece")

    def update_detailing(self, detailing_response: Dict):
        """Actualiza los campos de despiece automático"""
        if detailing_response.get("success") and detailing_response.get("results"):
            results = detailing_response["results"]

            self.detailing_computed = True
            self.detailing_results = results
            self.detailing_warnings = results.get("warnings", [])

            top_bars = results.get("top_bars", [])
            bottom_bars = results.get("bottom_bars", [])
            self.bar_detailing = {
                "top_bars": top_bars,
                "bottom_bars": bottom_bars,
            }

            self.prohibited_zones = results.get("prohibited_zones", [])
            self.material_list = results.get("material_list", [])

            self.total_bars_count = results.get("total_bars_count", 0)

            material_list = results.get("material_list", [])
            self.total_rebar_weight_kg = sum(item.get("weight_kg", 0) for item in material_list)

            waste_percentages = [item.get("waste_percentage", 0) for item in material_list]
            if waste_percentages:
                self.waste_percentage = sum(waste_percentages) / len(waste_percentages)

            self.optimization_score = self._calculate_optimization_score(results)

            self.detailing_computed_at = func.now()
            self.detailing_version = "1.0"

    def _calculate_optimization_score(self, results: Dict) -> float:
        """Calcula un score de optimización (0-100)"""
        score = 100.0

        warnings = results.get("warnings", [])
        score -= len(warnings) * 5

        material_list = results.get("material_list", [])
        avg_waste = sum(item.get("waste_percentage", 0) for item in material_list) / max(len(material_list), 1)
        if avg_waste > 15:
            score -= 20
        elif avg_waste > 10:
            score -= 10
        elif avg_waste > 5:
            score -= 5

        continuous_bars = results.get("continuous_bars", {})
        top_continuous = continuous_bars.get("top", {}).get("total_continuous", 0)
        bottom_continuous = continuous_bars.get("bottom", {}).get("total_continuous", 0)

        if top_continuous >= 2 and bottom_continuous >= 2:
            score += 10

        return max(0, min(100, score))
