from __future__ import annotations

from app.modules.drawing.domain import DimensionEntity
from app.modules.drawing.geometry import to_drawing_units


class DimensionRenderer:
    def __init__(
        self,
        offset_total_mm: float = 200.0,
        offset_spans_mm: float = 200.0,
        top_offset_mm: float = 200.0,
    ) -> None:
        self.offset_total_mm = offset_total_mm
        self.offset_spans_mm = offset_spans_mm
        self.top_offset_mm = top_offset_mm

    def draw(self, document, context) -> None:
        geometry = context.payload.geometry
        dim_layer = context.layer("dimensions")

        total_length = to_drawing_units(geometry.total_length_m, document.units)
        base_y = context.origin[1] - self.offset_total_mm
        document.add_entity(
            DimensionEntity(
                layer=dim_layer,
                start=(context.origin[0], base_y),
                end=(context.origin[0] + total_length, base_y),
                offset=25.0,
                text_override=f"{geometry.total_length_m:.2f}",
                metadata={"text_height": context.text_height_mm},
            )
        )

        span_offset = base_y - self.offset_spans_mm
        for span in geometry.spans:
            start_x = context.origin[0] + to_drawing_units(span.start_m, document.units)
            end_x = context.origin[0] + to_drawing_units(span.end_m, document.units)
            document.add_entity(
                DimensionEntity(
                    layer=dim_layer,
                    start=(start_x, span_offset),
                    end=(end_x, span_offset),
                    offset=20.0,
                    text_override=f"{span.clear_length_m:.2f}",
                    metadata={"text_height": context.text_height_mm},
                )
            )

        for support in geometry.supports:
            start_x = context.origin[0] + to_drawing_units(support.start_m, document.units)
            end_x = context.origin[0] + to_drawing_units(support.end_m, document.units)
            width_m = support.end_m - support.start_m
            if width_m <= 0:
                continue
            document.add_entity(
                DimensionEntity(
                    layer=dim_layer,
                    start=(start_x, span_offset),
                    end=(end_x, span_offset),
                    offset=20.0,
                    text_override=f"{width_m:.2f}",
                    metadata={"text_height": context.text_height_mm},
                )
            )

        self._draw_axis_dimensions(document, context, dim_layer)

    def _draw_axis_dimensions(self, document, context, layer: str) -> None:
        markers = sorted(context.payload.geometry.axis_markers, key=lambda m: m.position_m)
        if len(markers) < 2:
            return
        top_y = context.origin[1] + context.beam_height_mm + self.top_offset_mm
        for current, nxt in zip(markers, markers[1:]):
            start_x = context.origin[0] + to_drawing_units(current.position_m, document.units)
            end_x = context.origin[0] + to_drawing_units(nxt.position_m, document.units)
            length_m = nxt.position_m - current.position_m
            if length_m <= 0:
                continue
            document.add_entity(
                DimensionEntity(
                    layer=layer,
                    start=(start_x, top_y),
                    end=(end_x, top_y),
                    offset=20.0,
                    text_override=f"{length_m:.2f}",
                    metadata={"text_height": context.text_height_mm},
                )
            )


__all__ = ["DimensionRenderer"]
