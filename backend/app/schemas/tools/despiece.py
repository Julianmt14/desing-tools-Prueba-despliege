from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator

from app.schemas.design import DespieceVigaCreate


class BeamDetailPayload(DespieceVigaCreate):
    pass


class RebarDetail(BaseModel):
    """Detalle individual de una barra de refuerzo"""

    id: str = Field(..., description="Identificador único de la barra")
    diameter: str = Field(..., description="Diámetro de la barra (ej: '#6')")
    position: str = Field(..., description="Posición: 'top' o 'bottom'")
    type: str = Field(..., description="Tipo: 'continuous', 'support', 'span', 'segment'")
    length_m: float = Field(..., description="Longitud de la barra en metros")
    start_m: float = Field(..., description="Coordenada de inicio en metros")
    end_m: float = Field(..., description="Coordenada de fin en metros")
    quantity: int = Field(1, description="Cantidad de barras idénticas")
    splices: Optional[List[Dict[str, Any]]] = Field(None, description="Detalles de empalmes")
    hook_type: str = Field("135", description="Tipo de gancho: '90', '135', '180'")
    development_length_m: Optional[float] = Field(None, description="Longitud de desarrollo requerida")
    notes: Optional[str] = Field(None, description="Notas adicionales")

    @validator("position")
    def validate_position(cls, value: str) -> str:
        if value not in ["top", "bottom"]:
            raise ValueError('Position debe ser "top" o "bottom"')
        return value

    @validator("type")
    def validate_type(cls, value: str) -> str:
        valid_types = ["continuous", "support", "support_anchored", "span", "segment", "regular"]
        if value not in valid_types:
            raise ValueError(f'Tipo debe ser uno de: {", ".join(valid_types)}')
        return value

    @validator("hook_type")
    def validate_hook_type(cls, value: str) -> str:
        if value not in ["90", "135", "180"]:
            raise ValueError('Hook type debe ser "90", "135" o "180"')
        return value

    class Config:
        from_attributes = True


class ProhibitedZone(BaseModel):
    """Zona donde no se permiten empalmes según NSR-10"""

    start_m: float = Field(..., description="Inicio de la zona prohibida (m)")
    end_m: float = Field(..., description="Fin de la zona prohibida (m)")
    type: str = Field("no_splice_zone", description="Tipo de zona")
    description: str = Field(..., description="Descripción de la zona")
    support_index: Optional[int] = Field(None, description="Índice del apoyo asociado")

    @validator("end_m")
    def validate_end_greater_than_start(cls, value: float, values: Dict[str, Any]) -> float:
        if "start_m" in values and value <= values["start_m"]:
            raise ValueError("end_m debe ser mayor que start_m")
        return value

    class Config:
        from_attributes = True


class MaterialItem(BaseModel):
    """Item en la lista de materiales"""

    diameter: str = Field(..., description="Diámetro de la barra")
    total_length_m: float = Field(..., description="Longitud total requerida (m)")
    pieces: int = Field(..., description="Número total de piezas")
    weight_kg: float = Field(..., description="Peso total en kg")
    commercial_lengths: List[Dict[str, Any]] = Field(..., description="Optimización de cortes comerciales")
    waste_percentage: float = Field(..., description="Porcentaje de desperdicio")

    class Config:
        from_attributes = True


class StirrupSpanSpec(BaseModel):
    span_index: int = Field(..., description="Índice de la luz")
    label: str = Field(..., description="Etiqueta legible de la luz")
    base_cm: float = Field(..., description="Base bruta de la sección (cm)")
    height_cm: float = Field(..., description="Altura bruta de la sección (cm)")
    cover_cm: float = Field(..., description="Recubrimiento adoptado (cm)")
    stirrup_width_cm: float = Field(..., description="Ancho interno del estribo (cm)")
    stirrup_height_cm: float = Field(..., description="Altura interna del estribo (cm)")
    effective_depth_m: float = Field(..., description="d efectivo en metros")
    spacing_confined_m: float = Field(..., description="Separación d/4 para zonas confinadas (m)")
    spacing_non_confined_m: float = Field(..., description="Separación d/2 para zonas no confinadas (m)")

    class Config:
        from_attributes = True


class StirrupSegment(BaseModel):
    start_m: float = Field(..., description="Inicio del segmento (m)")
    end_m: float = Field(..., description="Fin del segmento (m)")
    zone_type: Literal["confined", "non_confined"] = Field(..., description="Tipo de zona")
    spacing_m: float = Field(..., description="Separación utilizada (m)")
    estimated_count: Optional[int] = Field(None, description="Cantidad estimada de estribos en el segmento")

    @validator("end_m")
    def validate_segment_length(cls, value: float, values: Dict[str, Any]) -> float:
        if "start_m" in values and value <= values["start_m"]:
            raise ValueError("end_m debe ser mayor que start_m")
        return value

    class Config:
        from_attributes = True


class StirrupDesignSummary(BaseModel):
    diameter: str = Field(..., description="Diámetro base del estribo")
    hook_type: str = Field(..., description="Tipo de gancho del estribo")
    additional_branches_total: int = Field(..., description="Ramas adicionales declaradas por el usuario")
    span_specs: List[StirrupSpanSpec] = Field(..., description="Geometría y d por luz")
    zone_segments: List[StirrupSegment] = Field(..., description="Distribución d/4 y d/2 a lo largo de la viga")

    class Config:
        from_attributes = True


class ContinuousBarsInfo(BaseModel):
    """Información sobre barras continuas"""

    diameters: List[str] = Field(..., description="Diámetros de barras continuas")
    count_per_diameter: Dict[str, int] = Field(..., description="Cantidad por diámetro")
    total_continuous: int = Field(..., description="Total de barras continuas")

    class Config:
        from_attributes = True


class DetailingResults(BaseModel):
    """Resultados completos del cálculo de despiece"""

    top_bars: List[RebarDetail] = Field(..., description="Barras superiores")
    bottom_bars: List[RebarDetail] = Field(..., description="Barras inferiores")
    prohibited_zones: List[ProhibitedZone] = Field(..., description="Zonas prohibidas para empalmes")
    material_list: List[MaterialItem] = Field(..., description="Lista de materiales optimizada")
    continuous_bars: Dict[str, ContinuousBarsInfo] = Field(..., description="Información de barras continuas")
    warnings: List[str] = Field(..., description="Advertencias NSR-10")
    validation_passed: bool = Field(..., description="Indica si pasa todas las validaciones")
    total_weight_kg: Optional[float] = Field(None, description="Peso total del acero (kg)")
    total_bars_count: Optional[int] = Field(None, description="Número total de barras")
    stirrups_summary: Optional[StirrupDesignSummary] = Field(None, description="Resumen de diseño de estribos")

    class Config:
        from_attributes = True


class DetailingRequest(BaseModel):
    """Solicitud de cálculo de despiece"""

    design_id: Optional[int] = Field(None, description="ID del diseño existente (opcional)")
    span_geometries: List[Dict[str, Any]] = Field(..., description="Geometría de las luces")
    axis_supports: List[Dict[str, Any]] = Field(..., description="Información de apoyos")
    top_bars_config: List[Dict[str, Any]] = Field(..., description="Configuración de barras superiores")
    bottom_bars_config: List[Dict[str, Any]] = Field(..., description="Configuración de barras inferiores")
    segment_reinforcements: Optional[List[Dict[str, Any]]] = Field(None, description="Refuerzo por segmento")
    has_initial_cantilever: bool = Field(False, description="Voladizo inicial")
    has_final_cantilever: bool = Field(False, description="Voladizo final")
    cover_cm: int = Field(4, description="Recubrimiento en cm")
    max_rebar_length_m: str = Field("12m", description="Longitud máxima de barra comercial")
    hook_type: str = Field("135", description="Tipo de gancho")
    energy_dissipation_class: str = Field("DES", description="Clase de disipación de energía")
    concrete_strength: str = Field("21 MPa (3000 psi)", description="Resistencia del concreto")
    reinforcement: str = Field("420 MPa (Grado 60)", description="Grado del acero")
    lap_splice_length_min_m: float = Field(0.75, description="Longitud mínima de traslape")

    class Config:
        from_attributes = True


class DetailingResponse(BaseModel):
    """Respuesta del cálculo de despiece"""

    success: bool = Field(..., description="Indica si el cálculo fue exitoso")
    results: Optional[DetailingResults] = Field(None, description="Resultados del cálculo")
    message: Optional[str] = Field(None, description="Mensaje informativo o de error")
    computation_time_ms: Optional[float] = Field(None, description="Tiempo de cálculo en milisegundos")

    class Config:
        from_attributes = True


class BeamPresetResponse(BaseModel):
    fc_options: List[str]
    fy_options: List[str]
    hook_options: List[str]
    max_bar_lengths: List[str]
    energy_classes: List[str] = Field(default=["DES", "DMO", "DMI"])
    diameter_options: List[str] = Field(default=["#3", "#4", "#5", "#6", "#7", "#8", "#9", "#10", "#11", "#14", "#18"])

    class Config:
        from_attributes = True
