from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

from app.modules.drawing.schemas import DrawingUnits

Point = Tuple[float, float]
DEFAULT_TOLERANCE = 1e-3
DEFAULT_BAR_STACK_GAP_MM = 12.0


def to_drawing_units(value_m: float, units: DrawingUnits) -> float:
    return round(value_m * units.scale_factor, units.precision)


def cm_to_drawing_units(value_cm: float, units: DrawingUnits) -> float:
    return to_drawing_units(value_cm / 100.0, units)


def clamp(value: float, precision: int) -> float:
    factor = 10**precision
    return round(value * factor) / factor


def offset(point: Point, dx: float = 0.0, dy: float = 0.0) -> Point:
    return (point[0] + dx, point[1] + dy)


def rectangle(origin: Point, width: float, height: float) -> list[Point]:
    x, y = origin
    return [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
        (x, y),
    ]


def chain_points(points: Sequence[Point]) -> list[Point]:
    chained: list[Point] = []
    for index, point in enumerate(points):
        if index == 0 or point != chained[-1]:
            chained.append(point)
    return chained


def points_from_m(points_m: Iterable[tuple[float, float]], units: DrawingUnits) -> list[Point]:
    converted: list[Point] = []
    for x_m, y_m in points_m:
        converted.append((to_drawing_units(x_m, units), to_drawing_units(y_m, units)))
    return converted


def midpoint(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


@dataclass(slots=True)
class CoordinateSpace:
    units: DrawingUnits
    origin: Point = (0.0, 0.0)

    def to_m(self, value: float) -> float:
        return value / self.units.scale_factor

    def from_m(self, value_m: float) -> float:
        return to_drawing_units(value_m, self.units)

    def from_cm(self, value_cm: float) -> float:
        return cm_to_drawing_units(value_cm, self.units)

    def point_from_m(self, x_m: float, y_m: float) -> Point:
        return (
            self.origin[0] + self.from_m(x_m),
            self.origin[1] + self.from_m(y_m),
        )

    def translate(self, point: Point, dx: float = 0.0, dy: float = 0.0) -> Point:
        return (point[0] + dx, point[1] + dy)


__all__ = [
    "CoordinateSpace",
    "DEFAULT_BAR_STACK_GAP_MM",
    "DEFAULT_TOLERANCE",
    "chain_points",
    "clamp",
    "cm_to_drawing_units",
    "midpoint",
    "offset",
    "points_from_m",
    "rectangle",
    "to_drawing_units",
]
