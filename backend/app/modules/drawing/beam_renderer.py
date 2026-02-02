from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.modules.drawing.domain import HatchEntity, PolylineEntity, TextEntity
from app.modules.drawing.geometry import rectangle, to_drawing_units


@dataclass(slots=True)
class BeamRendererConfig:
    hatch_pattern: str = "ANSI31"
    hatch_scale: float = 75.0


class BeamRenderer:
    def __init__(self, config: BeamRendererConfig | None = None) -> None:
        self.config = config or BeamRendererConfig()

    def draw(self, document, context) -> None:
        geometry = context.payload.geometry
        origin = context.origin
        total_length_mm = to_drawing_units(geometry.total_length_m, document.units)
        height_mm = context.beam_height_mm

        outline_layer = context.layer("beam_outline")
        outline_style = context.layer_style("beam_outline")
        outline = PolylineEntity(
            layer=outline_layer,
            points=rectangle(origin, total_length_mm, height_mm),
            closed=True,
            color=outline_style.color if outline_style else None,
            lineweight=outline_style.lineweight if outline_style else None,
        )
        document.add_entity(outline)

        hatch_layer = context.layer("beam_hatch")
        hatch = HatchEntity(
            layer=hatch_layer,
            boundary=rectangle(origin, total_length_mm, height_mm),
            pattern=self.config.hatch_pattern,
            scale=self.config.hatch_scale,
        )
        document.add_entity(hatch)

        self._draw_supports(document, context)
        self._draw_axis_markers(document, context)

    def _draw_supports(self, document, context) -> None:
        support_layer = context.layer("supports")
        style = context.layer_style("supports")
        y0 = context.origin[1]
        for support in context.payload.geometry.supports:
            start = to_drawing_units(support.start_m, document.units)
            width = to_drawing_units(support.width_m, document.units)
            points = rectangle((context.origin[0] + start, y0 - 20.0), width, 20.0)
            document.add_entity(
                PolylineEntity(
                    layer=support_layer,
                    points=points,
                    closed=True,
                    color=style.color if style else None,
                    lineweight=style.lineweight if style else None,
                )
            )

    def _draw_axis_markers(self, document, context) -> None:
        axis_layer = context.layer("axes")
        text_style = context.template.text_style("labels")
        style = context.layer_style("axes")
        for marker in context.payload.geometry.axis_markers:
            x = context.origin[0] + to_drawing_units(marker.position_m, document.units)
            top = context.origin[1] + context.beam_height_mm + 25.0
            bottom = context.origin[1] - 35.0
            document.add_entity(
                PolylineEntity(
                    layer=axis_layer,
                    points=[(x, bottom), (x, top)],
                    color=style.color if style else None,
                    lineweight=style.lineweight if style else None,
                )
            )
            document.add_entity(
                TextEntity(
                    layer=context.layer("text"),
                    content=marker.label,
                    insert=(x - 5.0, top + 10.0),
                    height=text_style.height,
                    style=text_style.name,
                )
            )


__all__ = ["BeamRenderer", "BeamRendererConfig"]
