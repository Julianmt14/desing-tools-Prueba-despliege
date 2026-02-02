from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from app.modules.drawing.schemas import DrawingUnits

Point = Tuple[float, float]


@dataclass
class DrawingEntity:
    layer: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineEntity(DrawingEntity):
    start: Point | None = None
    end: Point | None = None
    lineweight: float | None = None
    color: int | None = None


@dataclass
class PolylineEntity(DrawingEntity):
    points: Sequence[Point] = field(default_factory=list)
    closed: bool = False
    lineweight: float | None = None
    color: int | None = None


@dataclass
class TextEntity(DrawingEntity):
    content: str = ""
    insert: Point = (0.0, 0.0)
    height: float = 2.5
    rotation: float = 0.0
    style: str = "Standard"


@dataclass
class DimensionEntity(DrawingEntity):
    start: Point = (0.0, 0.0)
    end: Point = (0.0, 0.0)
    offset: float = 0.0
    text_override: str | None = None


@dataclass
class HatchEntity(DrawingEntity):
    boundary: Sequence[Point] = field(default_factory=list)
    pattern: str = "SOLID"
    scale: float = 1.0
    rotation: float = 0.0


@dataclass
class DrawingDocument:
    """Representa un documento vectorial independiente del formato final."""

    units: DrawingUnits
    scale: float = 50.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    entities: List[DrawingEntity] = field(default_factory=list)

    def add_entity(self, entity: DrawingEntity) -> None:
        self.entities.append(entity)

    def extend(self, new_entities: Sequence[DrawingEntity]) -> None:
        self.entities.extend(new_entities)


__all__ = [
    "DrawingDocument",
    "DrawingEntity",
    "DimensionEntity",
    "HatchEntity",
    "LineEntity",
    "Point",
    "PolylineEntity",
    "TextEntity",
]
