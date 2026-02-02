from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.modules.drawing.domain import LineEntity, TextEntity
from app.modules.drawing.geometry import to_drawing_units
from app.schemas.tools.despiece import RebarDetail


@dataclass(slots=True)
class _PreparedBar:
    bar: RebarDetail
    start_x: float
    end_x: float
    key: int
    quantity: int


@dataclass(slots=True)
class _GroupAccumulator:
    bar: RebarDetail
    start_x: float
    end_x: float
    quantity: int


class RebarDrawer:
    def __init__(
        self,
        *,
        top_line_offset_mm: float = 300.0,
        bottom_line_offset_mm: float = 300.0,
        lap_separation_mm: float = 90.0,
    ) -> None:
        self.top_line_offset_mm = top_line_offset_mm
        self.bottom_line_offset_mm = bottom_line_offset_mm
        self.lap_separation_mm = lap_separation_mm

    def draw(self, document, context) -> None:
        results = context.payload.detailing_results
        if not results:
            return

        layer_main = context.layer("rebar_main")
        layer_style = context.layer_style("rebar_main")
        text_style = context.template.text_style("labels")
        lane_spacing = self._lane_spacing(context)

        top_segments = self._prepare_segments(results.top_bars, document, context)
        bottom_segments = self._prepare_segments(results.bottom_bars, document, context)

        self._draw_group(
            document,
            context,
            top_segments,
            base_y=self._base_line_y(context, position="top"),
            direction=-1.0,
            lane_spacing=lane_spacing,
            layer=layer_main,
            layer_style=layer_style,
            text_style=text_style,
            position="top",
        )
        self._draw_group(
            document,
            context,
            bottom_segments,
            base_y=self._base_line_y(context, position="bottom"),
            direction=1.0,
            lane_spacing=lane_spacing,
            layer=layer_main,
            layer_style=layer_style,
            text_style=text_style,
            position="bottom",
        )

    def _prepare_segments(self, bars, document, context) -> List[_PreparedBar]:
        if not bars:
            return []
        origin_x = context.origin[0]
        grouped: Dict[tuple, _GroupAccumulator] = {}

        for bar in bars:
            if bar.start_m is None or bar.end_m is None:
                continue

            start_x = origin_x + to_drawing_units(bar.start_m, document.units)
            end_x = origin_x + to_drawing_units(bar.end_m, document.units)
            if end_x < start_x:
                start_x, end_x = end_x, start_x

            quantity = int(bar.quantity or 1)
            key = (
                bar.diameter,
                round(bar.start_m or 0.0, 4),
                round(bar.end_m or 0.0, 4),
                round(bar.length_m or 0.0, 4),
                bar.hook_type or "",
            )

            existing = grouped.get(key)
            if existing:
                existing.quantity += quantity
            else:
                grouped[key] = _GroupAccumulator(
                    bar=bar,
                    start_x=start_x,
                    end_x=end_x,
                    quantity=quantity,
                )

        prepared: List[_PreparedBar] = []
        for idx, accumulator in enumerate(
            sorted(grouped.values(), key=lambda item: (item.start_x, item.end_x))
        ):
            prepared.append(
                _PreparedBar(
                    bar=accumulator.bar,
                    start_x=accumulator.start_x,
                    end_x=accumulator.end_x,
                    key=idx,
                    quantity=accumulator.quantity,
                )
            )

        return prepared

    def _draw_group(
        self,
        document,
        context,
        segments: List[_PreparedBar],
        *,
        base_y: float,
        direction: float,
        lane_spacing: float,
        layer: str,
        layer_style,
        text_style,
        position: str,
    ) -> None:
        if not segments:
            return

        assignments = self._assign_lanes(segments)
        text_layer = context.layer("text")
        text_offset = (12.0 if position == "top" else -18.0) * context.vertical_scale

        for segment in segments:
            lane_index = assignments.get(segment.key, 0)
            y = base_y + direction * lane_spacing * lane_index
            bar = segment.bar
            document.add_entity(
                LineEntity(
                    layer=layer,
                    start=(segment.start_x, y),
                    end=(segment.end_x, y),
                    color=layer_style.color if layer_style else None,
                )
            )

            label = f"{segment.quantity}Φ{bar.diameter} L={bar.length_m:.2f}m"
            document.add_entity(
                TextEntity(
                    layer=text_layer,
                    content=label,
                    insert=(segment.start_x, y + text_offset),
                    height=context.text_height_mm,
                    style=text_style.name,
                )
            )

    def _assign_lanes(self, segments: List[_PreparedBar]) -> Dict[int, int]:
        assignments: Dict[int, int] = {}
        lane_ends: List[float] = []
        tolerance = 1e-3
        for item in sorted(segments, key=lambda s: (s.start_x, s.end_x)):
            lane_idx = None
            for idx, current_end in enumerate(lane_ends):
                if item.start_x >= current_end - tolerance:
                    lane_idx = idx
                    lane_ends[idx] = item.end_x
                    break
            if lane_idx is None:
                lane_ends.append(item.end_x)
                lane_idx = len(lane_ends) - 1
            assignments[item.key] = lane_idx
        return assignments

    def _lane_spacing(self, context) -> float:
        spacing = self.lap_separation_mm * max(context.vertical_scale, 1.0)
        return max(spacing, 1.0)

    def _base_line_y(self, context, *, position: str) -> float:
        offset_mm = (
            self.top_line_offset_mm if position == "top" else self.bottom_line_offset_mm
        ) * max(context.vertical_scale, 1.0)
        if position == "top":
            return context.origin[1] + context.beam_height_mm - offset_mm
        return context.origin[1] + offset_mm


__all__ = ["RebarDrawer"]
