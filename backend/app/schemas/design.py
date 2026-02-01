from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class SpanGeometry(BaseModel):
    label: str
    clear_span_between_supports_m: float = Field(..., ge=0)
    base_cm: float = Field(..., ge=0)
    height_cm: float = Field(..., ge=0)


class StirrupConfig(BaseModel):
    additional_branches: int = Field(0, ge=0)
    stirrup_type: Literal["C", "S"] = "C"

    @model_validator(mode="before")
    @classmethod
    def allow_legacy_schema(cls, data: Any) -> Any:
        """Permite convertir automáticamente configuraciones antiguas."""
        if not isinstance(data, dict):
            return data

        if "additional_branches" in data or "stirrup_type" in data:
            return data

        legacy_quantity = data.get("quantity")
        try:
            parsed_quantity = int(legacy_quantity)
        except (TypeError, ValueError):
            parsed_quantity = 0

        parsed_quantity = parsed_quantity if parsed_quantity >= 0 else 0

        return {
            "additional_branches": parsed_quantity,
            "stirrup_type": "C",
        }


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
    top_bars_qty: int
    bottom_bars_qty: int
    top_bar_diameters: Optional[List[str]] = None
    bottom_bar_diameters: Optional[List[str]] = None
    max_rebar_length_m: str = "12m"
    lap_splice_length_min_m: float = 0.75
    lap_splice_location: str = "Calculado automáticamente"
    beam_total_length_m: float = 0
    section_changes: Optional[List[Dict[str, Any]]] = None
    has_cantilevers: bool = False
    hook_type: str = "135"
    cover_cm: int = 4
    span_count: int = 1
    support_widths_cm: Optional[List[float]] = None
    span_geometries: List[Dict[str, Any]]
    axis_numbering: Optional[str] = None
    element_identifier: str
    element_level: Optional[float] = None
    element_quantity: int = 1
    reinforcement: str = "420 MPa (Grado 60)"
    stirrups_config: Optional[List[StirrupConfig]] = None
    segment_reinforcements: Optional[List[Dict[str, Any]]] = None
    energy_dissipation_class: str = "DES"
    concrete_strength: str = "21 MPa (3000 psi)"
    notes: Optional[str] = None
    detailing_computed: bool = False
    detailing_results: Optional[Dict[str, Any]] = None
    detailing_warnings: Optional[List[str]] = None
    bar_detailing: Optional[Dict[str, Any]] = None
    prohibited_zones: Optional[List[Dict[str, Any]]] = None
    material_list: Optional[List[Dict[str, Any]]] = None
    total_bars_count: Optional[int] = None
    total_rebar_weight_kg: Optional[float] = None
    waste_percentage: Optional[float] = None
    optimization_score: Optional[float] = None
    detailing_version: Optional[str] = None
    detailing_computed_at: Optional[datetime] = None


class DespieceVigaCreate(DespieceVigaBase):
    pass


class DespieceVigaUpdate(BaseModel):
    project_name: Optional[str] = None
    beam_label: Optional[str] = None
    top_bars_qty: Optional[int] = None
    bottom_bars_qty: Optional[int] = None
    top_bar_diameters: Optional[List[str]] = None
    bottom_bar_diameters: Optional[List[str]] = None
    max_rebar_length_m: Optional[str] = None
    lap_splice_length_min_m: Optional[float] = None
    lap_splice_location: Optional[str] = None
    beam_total_length_m: Optional[float] = None
    section_changes: Optional[List[Dict[str, Any]]] = None
    has_cantilevers: Optional[bool] = None
    hook_type: Optional[str] = None
    cover_cm: Optional[int] = None
    span_count: Optional[int] = None
    support_widths_cm: Optional[List[float]] = None
    span_geometries: Optional[List[Dict[str, Any]]] = None
    axis_numbering: Optional[str] = None
    element_identifier: Optional[str] = None
    element_level: Optional[float] = None
    element_quantity: Optional[int] = None
    reinforcement: Optional[str] = None
    stirrups_config: Optional[List[StirrupConfig]] = None
    segment_reinforcements: Optional[List[Dict[str, Any]]] = None
    energy_dissipation_class: Optional[str] = None
    concrete_strength: Optional[str] = None
    notes: Optional[str] = None
    detailing_computed: Optional[bool] = None
    detailing_results: Optional[Dict[str, Any]] = None
    detailing_warnings: Optional[List[str]] = None
    bar_detailing: Optional[Dict[str, Any]] = None
    prohibited_zones: Optional[List[Dict[str, Any]]] = None
    material_list: Optional[List[Dict[str, Any]]] = None
    total_bars_count: Optional[int] = None
    total_rebar_weight_kg: Optional[float] = None
    waste_percentage: Optional[float] = None
    optimization_score: Optional[float] = None
    detailing_version: Optional[str] = None
    detailing_computed_at: Optional[datetime] = None


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
