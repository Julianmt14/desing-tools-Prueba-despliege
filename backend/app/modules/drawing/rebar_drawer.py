from __future__ import annotations

from collections import defaultdict

from app.modules.drawing.domain import LineEntity, TextEntity
from app.modules.drawing.geometry import DEFAULT_BAR_STACK_GAP_MM, to_drawing_units


class RebarDrawer:
    def __init__(self, stack_gap_mm: float = DEFAULT_BAR_STACK_GAP_MM) -> None:
        self.stack_gap_mm = stack_gap_mm

    def draw(self, document, context) -> None:
        results = context.payload.detailing_results
        if not results:
            return

        layer_main = context.layer("rebar_main")
        layer_style = context.layer_style("rebar_main")
        text_style = context.template.text_style("labels")
        counters = defaultdict(int)
        gap = self.stack_gap_mm * context.vertical_scale

        def bar_y(position: str, index: int) -> float:
            if position == "top":
                return context.origin[1] + context.beam_height_mm - context.cover_mm - index * gap
            return context.origin[1] + context.cover_mm + index * gap

        for bar in list(results.top_bars) + list(results.bottom_bars):
            counters[bar.position] += 1
            idx = counters[bar.position] - 1
            y = bar_y(bar.position, idx)
            start_x = context.origin[0] + to_drawing_units(bar.start_m, document.units)
            end_x = context.origin[0] + to_drawing_units(bar.end_m, document.units)

            document.add_entity(
                LineEntity(
                    layer=layer_main,
                    start=(start_x, y),
                    end=(end_x, y),
                    color=layer_style.color if layer_style else None,
                )
            )

            label = f"{bar.id} Φ{bar.diameter} L={bar.length_m:.2f}m"
            text_offset = (12.0 if bar.position == "top" else -18.0) * context.vertical_scale
            document.add_entity(
                TextEntity(
                    layer=context.layer("text"),
                    content=label,
                    insert=(start_x, y + text_offset),
                    height=context.text_height_mm,
                    style=text_style.name,
                )
            )


__all__ = ["RebarDrawer"]
