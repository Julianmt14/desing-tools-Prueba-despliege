from __future__ import annotations

from dataclasses import dataclass
import math

from app.modules.drawing.domain import PolylineEntity, TextEntity


@dataclass(slots=True)
class TitleBlockConfig:
    width_mm: float = 2400.0
    height_mm: float = 90.0  # fallback
    margin_mm: float = 35.0


class TitleBlockRenderer:
    def __init__(self, config: TitleBlockConfig | None = None) -> None:
        self.config = config or TitleBlockConfig()

    def draw(self, document, context) -> None:
        layer = context.layer("title_block")
        style = context.layer_style("title_block")
        text_style = context.template.text_style("title")

        width = self.config.width_mm
        height = context.beam_height_mm or self.config.height_mm
        right_x = context.origin[0]
        origin_x = right_x - width
        top_y = context.origin[1] + height
        origin_y = top_y - height
        radius = 150.0
        right = origin_x + width
        bottom = origin_y
        top = origin_y + height
        top_left_center = (origin_x + radius, top - radius)
        bottom_left_center = (origin_x + radius, bottom + radius)

        def arc_points(center, start_deg, end_deg, segments=4):
            (cx, cy) = center
            step = (end_deg - start_deg) / segments
            return [
                (
                    cx + radius * math.cos(math.radians(start_deg + step * i)),
                    cy + radius * math.sin(math.radians(start_deg + step * i)),
                )
                for i in range(segments + 1)
            ]

        block_points = [
            (origin_x + radius, bottom),
            (right, bottom),
            (right, top),
            (origin_x + radius, top),
        ]
        block_points.extend(arc_points(top_left_center, 90.0, 180.0)[1:])
        block_points.append((origin_x, bottom + radius))
        block_points.extend(arc_points(bottom_left_center, 180.0, 270.0)[1:])

        document.add_entity(
            PolylineEntity(
                layer=layer,
                points=block_points,
                closed=True,
                color=style.color if style else None,
                lineweight=style.lineweight if style else None,
            )
        )

        metadata = context.payload.metadata
        geometry = context.payload.geometry
        section_width_cm = geometry.spans[0].section_width_cm if geometry.spans else None
        section_height_cm = geometry.spans[0].section_height_cm if geometry.spans else None
        if section_width_cm is not None and section_height_cm is not None:
            section_text = f"Sección: {section_width_cm:.0f} cm x {section_height_cm:.0f} cm"
        else:
            section_text = "Sección: N/D"

        lines = [
            f"Viga: {metadata.beam_label}",
            f"Nivel: {metadata.element_level if metadata.element_level is not None else 'N/A'}",
            section_text,
            f"Cantidad: {metadata.element_quantity} vigas",
        ]

        padding_y = 220.0
        padding_x = 150.0
        line_spacing = 400.0
        cursor_y = top_y - padding_y
        for line in lines:
            document.add_entity(
                TextEntity(
                    layer=context.layer("text"),
                    content=line,
                    insert=(origin_x + padding_x, cursor_y),
                    height=context.text_height_mm,
                    style=text_style.name,
                )
            )
            cursor_y -= line_spacing


__all__ = ["TitleBlockRenderer", "TitleBlockConfig"]
