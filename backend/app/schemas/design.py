from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SpanGeometry(BaseModel):
    label: str
    clear_span_between_supports_m: float = Field(..., ge=0)
    base_cm: float = Field(..., ge=0)
    height_cm: float = Field(..., ge=0)


class StirrupZone(BaseModel):
    zone: str
    spacing_m: float = Field(..., gt=0)
    quantity: int = Field(..., ge=1)


class SegmentRebarConfig(BaseModel):
    quantity: int = Field(..., ge=1)
    diameter: str


class SegmentReinforcement(BaseModel):
    span_indexes: list[int] = Field(..., min_length=1)
    top_rebar: SegmentRebarConfig | None = None
    bottom_rebar: SegmentRebarConfig | None = None

    @model_validator(mode="after")
    def ensure_rebar_defined(self) -> "SegmentReinforcement":
        if not self.top_rebar and not self.bottom_rebar:
            raise ValueError("Debe definir al menos un refuerzo superior o inferior")
        return self


class DespieceVigaBase(BaseModel):
    project_name: str
    beam_label: str
    top_bars_qty: int = Field(..., ge=0)
    bottom_bars_qty: int = Field(..., ge=0)
    top_bar_diameters: list[str] | None = None
    bottom_bar_diameters: list[str] | None = None
    max_rebar_length_m: str
    lap_splice_length_min_m: float = Field(..., gt=0)
    lap_splice_location: str
    beam_total_length_m: float = Field(..., ge=0)
    section_changes: list[SpanGeometry] | None = None
    has_cantilevers: bool = False
    hook_type: str
    cover_cm: int = Field(..., ge=0)
    span_count: int = Field(..., ge=1)
    support_widths_cm: list[float] | None = None
    span_geometries: list[SpanGeometry] = Field(default_factory=list)
    axis_numbering: str | None = None
    element_identifier: str
    element_level: float | None = Field(default=None)
    element_quantity: int = Field(default=1, ge=1)
    reinforcement: str
    stirrups_config: list[StirrupZone] = Field(default_factory=list)
    segment_reinforcements: list[SegmentReinforcement] | None = None
    energy_dissipation_class: str
    concrete_strength: str
    notes: str | None = None


class DespieceVigaCreate(DespieceVigaBase):
    pass


class DespieceVigaUpdate(BaseModel):
    project_name: str | None = None
    beam_label: str | None = None
    top_bars_qty: int | None = Field(default=None, ge=0)
    bottom_bars_qty: int | None = Field(default=None, ge=0)
    top_bar_diameters: list[str] | None = None
    bottom_bar_diameters: list[str] | None = None
    max_rebar_length_m: str | None = None
    lap_splice_length_min_m: float | None = Field(default=None, gt=0)
    lap_splice_location: str | None = None
    beam_total_length_m: float | None = Field(default=None, ge=0)
    section_changes: list[SpanGeometry] | None = None
    has_cantilevers: bool | None = None
    hook_type: str | None = None
    cover_cm: int | None = Field(default=None, ge=0)
    span_count: int | None = Field(default=None, ge=1)
    support_widths_cm: list[float] | None = None
    span_geometries: list[SpanGeometry] | None = None
    axis_numbering: str | None = None
    element_identifier: str | None = None
    element_level: float | None = Field(default=None)
    element_quantity: int | None = Field(default=None, ge=1)
    reinforcement: str | None = None
    stirrups_config: list[StirrupZone] | None = None
    segment_reinforcements: list[SegmentReinforcement] | None = None
    energy_dissipation_class: str | None = None
    concrete_strength: str | None = None
    notes: str | None = None


class DespieceVigaRead(DespieceVigaBase):
    id: int
    design_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DesignBase(BaseModel):
    title: str
    description: str | None = None
    design_type: str
    settings: dict[str, Any] = Field(default_factory=dict)


class DesignCreate(DesignBase):
    despiece_viga: DespieceVigaCreate | None = None


class DesignRead(DesignBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    thumbnail_url: str | None = None
    despiece_viga: DespieceVigaRead | None = None

    class Config:
        from_attributes = True
