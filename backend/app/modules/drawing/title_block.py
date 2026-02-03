from __future__ import annotations

from dataclasses import dataclass
import math

from app.modules.drawing.domain import PolylineEntity, TextEntity
from app.modules.drawing.geometry import to_drawing_units


def rounded_rect_points(x_min, y_min, width, height, radius, segments=4):
    x_max = x_min + width
    y_max = y_min + height
    if width <= 0 or height <= 0:
        return []
    radius = max(0.0, min(radius, width / 2.0, height / 2.0))

    def arc(center, start_deg, end_deg):
        (cx, cy) = center
        step = (end_deg - start_deg) / segments
        return [
            (
                cx + radius * math.cos(math.radians(start_deg + step * i)),
                cy + radius * math.sin(math.radians(start_deg + step * i)),
            )
            for i in range(segments + 1)
        ]

    if radius == 0:
        return [
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max),
        ]

    points = [(x_min + radius, y_min), (x_max - radius, y_min)]
    points.extend(arc((x_max - radius, y_min + radius), 270.0, 360.0)[1:])
    points.append((x_max, y_max - radius))
    points.extend(arc((x_max - radius, y_max - radius), 0.0, 90.0)[1:])
    points.append((x_min + radius, y_max))
    points.extend(arc((x_min + radius, y_max - radius), 90.0, 180.0)[1:])
    points.append((x_min, y_min + radius))
    points.extend(arc((x_min + radius, y_min + radius), 180.0, 270.0)[1:])
    return points


@dataclass(slots=True)
class TitleBlockConfig:
    width_mm: float = 2400.0
    height_mm: float = 90.0  # fallback
    margin_mm: float = 35.0
    inner_offset_mm: float = 70.0


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

        self._draw_inner_outline(
            document,
            layer,
            style,
            origin_x,
            bottom,
            width,
            height,
            radius,
        )

        metadata = context.payload.metadata
        geometry = context.payload.geometry
        section_width_cm = geometry.spans[0].section_width_cm if geometry.spans else None
        section_height_cm = geometry.spans[0].section_height_cm if geometry.spans else None
        if section_width_cm is not None and section_height_cm is not None:
            section_text = f"b={section_width_cm / 100:.2f} h={section_height_cm / 100:.2f}"
        else:
            section_text = "Sección: N/D"

        lines = [
            f"{metadata.beam_label}",
            f"Nivel: {metadata.element_level if metadata.element_level is not None else 'N/A'}",
            section_text,
            f"Cantidad: {metadata.element_quantity}",
        ]

        padding_y = 220.0
        line_spacing = 400.0
        cursor_y = top_y - padding_y
        text_positions: list[tuple[str, float]] = []
        top_lines = lines[:2]
        for idx, line in enumerate(top_lines):
            text_positions.append((line, cursor_y - idx * line_spacing - 100.0))

        quantity_y = bottom + 250.0
        section_y = quantity_y + 250.0
        text_positions.append((lines[2], section_y))
        text_positions.append((lines[3], quantity_y))

        for content, pos_y in text_positions:
            insert_point = (origin_x + width / 2.0, pos_y)
            document.add_entity(
                TextEntity(
                    layer=context.layer("text"),
                    content=content,
                    insert=insert_point,
                    height=context.text_height_mm,
                    style=text_style.name,
                    metadata={
                        "halign": 1,
                        "align_point": insert_point,
                    },
                )
            )

    def _draw_inner_outline(self, document, layer, style, origin_x, bottom, width, height, outer_radius):
        offset = self.config.inner_offset_mm
        if width <= 2 * offset or height <= 2 * offset:
            return
        inner_left = origin_x + offset
        inner_bottom = bottom + offset
        inner_width = width - 2 * offset
        inner_height = height - 2 * offset
        inner_radius = max(outer_radius - offset, 0.0)
        if inner_radius == 0:
            inner_radius = min(inner_width, inner_height) * 0.1
        points = rounded_rect_points(inner_left, inner_bottom, inner_width, inner_height, inner_radius)
        if not points:
            return
        document.add_entity(
            PolylineEntity(
                layer=layer,
                points=points,
                closed=True,
                color=style.color if style else None,
                lineweight=style.lineweight if style else None,
            )
        )


@dataclass(slots=True)
class RightInfoBoxConfig:
    width_mm: float = 2600.0
    corner_radius_mm: float = 150.0
    bottom_padding_mm: float = 170.0
    line_spacing_mm: float = 170.0
    inner_offset_mm: float = 70.0


class RightInfoBoxRenderer:
    def __init__(self, config: RightInfoBoxConfig | None = None) -> None:
        self.config = config or RightInfoBoxConfig()

    def draw(self, document, context) -> None:
        layer = context.layer("title_block")
        style = context.layer_style("title_block")
        text_style = context.template.text_style("title")
        text_layer = context.layer("text")

        height = context.beam_height_mm
        if height <= 0:
            return

        total_length_m = getattr(context.payload.geometry, "total_length_m", 0.0) or 0.0
        beam_length_mm = to_drawing_units(total_length_m, document.units)
        origin_x = context.origin[0] + beam_length_mm
        bottom = context.origin[1]
        top = bottom + height
        width = self.config.width_mm
        right = origin_x + width
        radius = self.config.corner_radius_mm
        top_right_center = (right - radius, top - radius)
        bottom_right_center = (right - radius, bottom + radius)

        def arc_points(center, start_deg, end_deg, segments: int = 4):
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
            (origin_x, bottom),
            (right - radius, bottom),
        ]
        block_points.extend(arc_points(bottom_right_center, 270.0, 360.0)[1:])
        block_points.append((right, top - radius))
        block_points.extend(arc_points(top_right_center, 0.0, 90.0)[1:])
        block_points.append((right - radius, top))
        block_points.append((origin_x, top))

        document.add_entity(
            PolylineEntity(
                layer=layer,
                points=block_points,
                closed=True,
                color=style.color if style else None,
                lineweight=style.lineweight if style else None,
            )
        )

        self._draw_inner_outline(
            document,
            layer,
            style,
            origin_x,
            bottom,
            width,
            height,
            radius,
        )

        steel_insert = (
            origin_x + width / 2.0,
            bottom + self.config.bottom_padding_mm,
        )
        document.add_entity(
            TextEntity(
                layer=text_layer,
                content=self._steel_text(context),
                insert=steel_insert,
                height=context.text_height_mm * 0.85,
                style=text_style.name,
                metadata={
                    "halign": 1,
                    "align_point": steel_insert,
                },
            )
        )

        concrete_insert = (
            steel_insert[0],
            steel_insert[1] + self.config.line_spacing_mm,
        )
        document.add_entity(
            TextEntity(
                layer=text_layer,
                content=self._concrete_text(context),
                insert=concrete_insert,
                height=context.text_height_mm * 0.85,
                style=text_style.name,
                metadata={
                    "halign": 1,
                    "align_point": concrete_insert,
                },
            )
        )

        label_insert = (
            concrete_insert[0],
            concrete_insert[1] + self.config.line_spacing_mm,
        )
        document.add_entity(
            TextEntity(
                layer=text_layer,
                content=self._stirrup_summary_text(context),
                insert=label_insert,
                height=context.text_height_mm,
                style=text_style.name,
                metadata={
                    "halign": 1,
                    "align_point": label_insert,
                },
            )
        )

    def _draw_inner_outline(self, document, layer, style, origin_x, bottom, width, height, outer_radius):
        offset = self.config.inner_offset_mm
        if width <= 2 * offset or height <= 2 * offset:
            return
        inner_left = origin_x + offset
        inner_bottom = bottom + offset
        inner_width = width - 2 * offset
        inner_height = height - 2 * offset
        inner_radius = max(outer_radius - offset, 0.0)
        if inner_radius == 0:
            inner_radius = min(inner_width, inner_height) * 0.1
        points = rounded_rect_points(inner_left, inner_bottom, inner_width, inner_height, inner_radius)
        if not points:
            return
        document.add_entity(
            PolylineEntity(
                layer=layer,
                points=points,
                closed=True,
                color=style.color if style else None,
                lineweight=style.lineweight if style else None,
            )
        )

    def _stirrup_summary_text(self, context) -> str:
        summary = getattr(getattr(context.payload, "detailing_results", None), "stirrups_summary", None)
        geometry = context.payload.geometry
        diameter = getattr(summary, "diameter", "#3")
        gauge_text = diameter
        if diameter.startswith("#"):
            try:
                gauge = float(diameter.replace("#", ""))
                if gauge == 3:
                    gauge_text = "Ø3/8\""
                elif gauge == 4:
                    gauge_text = "Ø1/2\""
            except ValueError:
                gauge_text = diameter
        total_count = 0
        total_length_m = 0.0
        if summary and summary.zone_segments:
            for segment in summary.zone_segments:
                count = segment.estimated_count or 0
                total_count += count
                segment_length = max(float(segment.end_m) - float(segment.start_m), 0.0)
                total_length_m += segment_length
        spacing_m = 0.0
        if geometry.spans:
            spacing_m = geometry.spans[0].section_height_cm / 100.0 if geometry.spans[0].section_height_cm else 0.0
        stirrup_length_m = max(spacing_m * 3.0, 1.0)
        text_total = max(total_count, 0)
        return f"{text_total} Flejes {gauge_text} L={stirrup_length_m:.2f}m"

    def _concrete_text(self, context) -> str:
        fc = context.payload.metadata.concrete_strength or "N/D"
        return f"f'c={fc}"

    def _steel_text(self, context) -> str:
        fy = context.payload.metadata.reinforcement or "N/D"
        return f"f'y={fy}"


__all__ = ["TitleBlockRenderer", "TitleBlockConfig", "RightInfoBoxRenderer", "RightInfoBoxConfig"]
