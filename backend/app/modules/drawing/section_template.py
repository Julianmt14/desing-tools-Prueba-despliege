from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import ezdxf

from app.modules.drawing.domain import PolylineEntity, TextEntity

Point = Tuple[float, float]


class SectionTemplateError(RuntimeError):
    """Errores asociados al cargue del template de sección."""


@dataclass(slots=True)
class TemplatePolyline:
    layer: str
    points: Sequence[Point]
    closed: bool = False

    def instantiate(self, scale: float, offset: Point, target_layer: str | None) -> PolylineEntity:
        ox, oy = offset
        scaled = [(ox + scale * x, oy + scale * y) for (x, y) in self.points]
        layer = target_layer or self.layer
        return PolylineEntity(layer=layer, points=scaled, closed=self.closed)


@dataclass(slots=True)
class TemplateText:
    layer: str
    content: str
    insert: Point
    height: float
    rotation: float
    attachment_point: int | None
    placeholder: str | None

    def instantiate(
        self,
        scale: float,
        offset: Point,
        text_layer: str | None,
        text_style: str,
        replacements: Dict[str, str],
    ) -> TextEntity:
        ox, oy = offset
        insert = (ox + scale * self.insert[0], oy + scale * self.insert[1])
        content = replacements.get(self.placeholder, self.content) if self.placeholder else self.content
        metadata = _attachment_metadata(self.attachment_point, insert)
        layer = text_layer or self.layer
        return TextEntity(
            layer=layer,
            content=content,
            insert=insert,
            height=self.height * scale,
            rotation=self.rotation,
            style=text_style,
            metadata=metadata,
        )


@dataclass(slots=True)
class SectionTemplate:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    polylines: List[TemplatePolyline]
    texts: List[TemplateText]

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    def instantiate(
        self,
        *,
        scale: float,
        offset: Point,
        shape_layer: str,
        text_layer: str,
        text_style: str,
        placeholders: Dict[str, str],
    ) -> List[TextEntity | PolylineEntity]:
        entities: List[TextEntity | PolylineEntity] = []
        for poly in self.polylines:
            entities.append(poly.instantiate(scale, offset, shape_layer))
        for text in self.texts:
            entities.append(text.instantiate(scale, offset, text_layer, text_style, placeholders))
        return entities


def get_section_template() -> SectionTemplate:
    return _load_template()


@lru_cache()
def _load_template() -> SectionTemplate:
    template_path = Path(__file__).resolve().parents[3] / "assets" / "section_template.dxf"
    if not template_path.exists():
        raise SectionTemplateError(f"No se encontró el template DXF en {template_path}")

    doc = ezdxf.readfile(template_path)
    msp = doc.modelspace()

    polylines: List[TemplatePolyline] = []
    texts: List[TemplateText] = []
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    def extend_bounds(points: Iterable[Point]) -> None:
        nonlocal min_x, min_y, max_x, max_y
        for x, y in points:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    for entity in msp:
        kind = entity.dxftype()
        if kind == "LWPOLYLINE":
            vertices = [(vec[0], vec[1]) for vec in entity.vertices()]
            polylines.append(TemplatePolyline(layer=entity.dxf.layer, points=vertices, closed=entity.closed))
            extend_bounds(vertices)
        elif kind == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            points = [(start[0], start[1]), (end[0], end[1])]
            polylines.append(TemplatePolyline(layer=entity.dxf.layer, points=points, closed=False))
            extend_bounds(points)
        elif kind == "CIRCLE":
            center = entity.dxf.center
            radius = float(entity.dxf.radius)
            points = _circle_points((center[0], center[1]), radius)
            polylines.append(TemplatePolyline(layer=entity.dxf.layer, points=points, closed=True))
            extend_bounds(points)
        elif kind == "MTEXT":
            insert = entity.dxf.insert
            content = entity.plain_text().strip()
            texts.append(
                TemplateText(
                    layer=entity.dxf.layer,
                    content=content,
                    insert=(insert[0], insert[1]),
                    height=float(getattr(entity.dxf, "char_height", 30.0)),
                    rotation=float(getattr(entity.dxf, "rotation", 0.0)),
                    attachment_point=getattr(entity.dxf, "attachment_point", None),
                    placeholder=_extract_placeholder(content),
                )
            )
            extend_bounds([(insert[0], insert[1])])

    if not polylines and not texts:
        raise SectionTemplateError("El template DXF no contiene entidades procesables")

    if math.isinf(min_x) or math.isinf(min_y):
        min_x = min_y = 0.0
    if math.isinf(max_x) or math.isinf(max_y):
        max_x = max_y = 0.0

    return SectionTemplate(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y, polylines=polylines, texts=texts)


def _circle_points(center: Point, radius: float, segments: int = 48) -> List[Point]:
    cx, cy = center
    points: List[Point] = []
    for idx in range(segments + 1):
        angle = 2 * math.pi * (idx / segments)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def _extract_placeholder(content: str) -> str | None:
    stripped = content.strip()
    if stripped.startswith("{{") and stripped.endswith("}}"):
        return stripped.replace("{{", "").replace("}}", "")
    return None


def _attachment_metadata(attachment: int | None, align_point: Point) -> Dict[str, int | Point]:
    if attachment is None:
        return {"align_point": align_point}
    halign_map = {
        1: 0,
        2: 1,
        3: 2,
        4: 0,
        5: 1,
        6: 2,
        7: 0,
        8: 1,
        9: 2,
    }
    valign_map = {
        1: 3,
        2: 3,
        3: 3,
        4: 2,
        5: 2,
        6: 2,
        7: 1,
        8: 1,
        9: 1,
    }
    halign = halign_map.get(attachment)
    valign = valign_map.get(attachment)
    metadata: Dict[str, int | Point] = {"align_point": align_point}
    if halign is not None:
        metadata["halign"] = halign
    if valign is not None:
        metadata["valign"] = valign
    return metadata


__all__ = ["SectionTemplate", "SectionTemplateError", "get_section_template"]
