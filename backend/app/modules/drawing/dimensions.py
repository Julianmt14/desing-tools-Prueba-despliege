from __future__ import annotations

from app.modules.drawing.domain import DimensionEntity, TextEntity
from app.modules.drawing.geometry import to_drawing_units


class DimensionRenderer:
    def __init__(self, offset_total_mm: float = 60.0, offset_spans_mm: float = 90.0) -> None:
        self.offset_total_mm = offset_total_mm
        self.offset_spans_mm = offset_spans_mm

    def draw(self, document, context) -> None:
        geometry = context.payload.geometry
        dim_layer = context.layer("dimensions")
        text_style = context.template.text_style("dimensions", fallback="labels")

        total_length = to_drawing_units(geometry.total_length_m, document.units)
        base_y = context.origin[1] - self.offset_total_mm
        document.add_entity(
            DimensionEntity(
                layer=dim_layer,
                start=(context.origin[0], base_y),
                end=(context.origin[0] + total_length, base_y),
                offset=25.0,
                text_override=f"{geometry.total_length_m:.2f} m",
            )
        )
        document.add_entity(
            TextEntity(
                layer=context.layer("text"),
                content="Longitud total",
                insert=(context.origin[0], base_y - 10.0),
                height=text_style.height,
                style=text_style.name,
            )
        )

        span_offset = context.origin[1] - self.offset_spans_mm
        for span in geometry.spans:
            start_x = context.origin[0] + to_drawing_units(span.start_m, document.units)
            end_x = context.origin[0] + to_drawing_units(span.end_m, document.units)
            document.add_entity(
                DimensionEntity(
                    layer=dim_layer,
                    start=(start_x, span_offset),
                    end=(end_x, span_offset),
                    offset=20.0,
                    text_override=f"{span.clear_length_m:.2f} m",
                )
            )
            document.add_entity(
                TextEntity(
                    layer=context.layer("text"),
                    content=span.label,
                    insert=(start_x, span_offset - 12.0),
                    height=text_style.height,
                    style=text_style.name,
                )
            )


__all__ = ["DimensionRenderer"]
