from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.design import SegmentReinforcement, StirrupConfig
from app.schemas.tools.despiece import DetailingResults


class DrawingUnits(BaseModel):
    """Describe la relación de unidades usada por el motor de dibujo."""

    source_unit: Literal["m", "cm"] = "m"
    target_unit: Literal["mm", "cm"] = "mm"
    scale_factor: float = Field(1000.0, gt=0)
    precision: int = Field(2, ge=0, le=6)


class BeamDrawingMetadata(BaseModel):
    project_name: str
    beam_label: str
    element_identifier: str
    element_level: Optional[float] = Field(None, description="Nivel de referencia en metros")
    element_quantity: int = 1
    axis_labels: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    concrete_strength: str
    reinforcement: str
    energy_dissipation_class: str
    updated_at: Optional[datetime] = None


class AxisMarker(BaseModel):
    index: int
    label: str
    position_m: float


class BeamSupport(BaseModel):
    index: int
    label: str
    width_m: float
    start_m: float
    end_m: float


class BeamSpan(BaseModel):
    index: int
    label: str
    start_support_index: int
    end_support_index: int
    clear_length_m: float
    start_m: float
    end_m: float
    section_width_cm: float
    section_height_cm: float


class BeamGeometry(BaseModel):
    total_length_m: float
    spans: List[BeamSpan]
    supports: List[BeamSupport]
    axis_markers: List[AxisMarker] = Field(default_factory=list)
    has_cantilevers: bool = False


class RebarGroup(BaseModel):
    diameter: str
    quantity: int
    position: Literal["top", "bottom"]
    notes: Optional[str] = None


class BeamRebarLayout(BaseModel):
    top_groups: List[RebarGroup]
    bottom_groups: List[RebarGroup]
    hook_type: str
    cover_cm: int
    lap_splice_length_min_m: float
    max_rebar_length_m: float
    segment_reinforcements: Optional[List[SegmentReinforcement]] = None


class BeamDrawingPayload(BaseModel):
    design_id: int
    despiece_id: int
    metadata: BeamDrawingMetadata
    geometry: BeamGeometry
    rebar_layout: BeamRebarLayout
    detailing_results: Optional[DetailingResults] = None
    stirrups_config: Optional[List[StirrupConfig]] = None
    drawing_units: DrawingUnits = Field(default_factory=DrawingUnits)


class DrawingExportRequest(BaseModel):
    design_id: int
    format: Literal["dwg", "dxf", "pdf"] = "dwg"
    template: str = Field("beam/default", description="Identificador de la plantilla de layout")
    scale: float = Field(50.0, gt=0)
    locale: Literal["es-CO", "en-US"] = "es-CO"
    include_preview: bool = False


class DrawingExportResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    message: Optional[str] = None
