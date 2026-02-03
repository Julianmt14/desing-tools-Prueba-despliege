from __future__ import annotations

from dataclasses import dataclass
import logging
import math

from app.modules.drawing.domain import PolylineEntity, TextEntity
from app.modules.drawing.geometry import to_drawing_units
from app.modules.drawing.section_template import SectionTemplateError, get_section_template

logger = logging.getLogger(__name__)


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
        beam_label_y = top_y - padding_y - 100.0
        level_y = top - (height * 0.30)
        section_y = bottom + (height * 0.30)
        quantity_y = bottom + 250.0

        text_positions: list[tuple[str, float]] = [
            (lines[0], beam_label_y),
            (lines[1], level_y),
            (lines[2], section_y),
            (lines[3], quantity_y),
        ]

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

        self._draw_section_schematic(
            document,
            context,
            origin_x,
            bottom,
            width,
            top,
            label_insert[1],
        )

    def _section_schematic_data(self, context):
        geometry = context.payload.geometry
        spans = geometry.spans or []
        base_cm = spans[0].section_width_cm if spans else 30.0
        height_cm = spans[0].section_height_cm if spans else 45.0
        rebar_layout = getattr(context.payload, "rebar_layout", None)
        cover_cm = getattr(rebar_layout, "cover_cm", None) or 4.0
        detailing = getattr(context.payload, "detailing_results", None)
        summary = getattr(detailing, "stirrups_summary", None) if detailing else None
        stirrup_width_cm = None
        stirrup_height_cm = None
        hook_type = "135"
        stirrup_diameter = "#3"
        if summary:
            hook_type = summary.hook_type or hook_type
            stirrup_diameter = summary.diameter or stirrup_diameter
            if summary.span_specs:
                spec = summary.span_specs[0]
                stirrup_width_cm = spec.stirrup_width_cm
                stirrup_height_cm = spec.stirrup_height_cm
                cover_cm = spec.cover_cm or cover_cm
                base_cm = spec.base_cm or base_cm
                height_cm = spec.height_cm or height_cm
        if not stirrup_width_cm:
            stirrup_width_cm = max(base_cm - 2 * cover_cm, base_cm * 0.7)
        if not stirrup_height_cm:
            stirrup_height_cm = max(height_cm - 2 * cover_cm, height_cm * 0.7)
        return {
            "base_mm": base_cm * 10.0,
            "height_mm": height_cm * 10.0,
            "cover_mm": cover_cm * 10.0,
            "stirrup_width_mm": stirrup_width_cm * 10.0,
            "stirrup_height_mm": stirrup_height_cm * 10.0,
            "hook_type": hook_type,
            "stirrup_diameter": stirrup_diameter,
        }

    def _draw_section_schematic(self, document, context, box_left, box_bottom, box_width, box_top, reference_y):
        data = self._section_schematic_data(context)
        try:
            template = get_section_template()
        except SectionTemplateError as exc:  # pragma: no cover - dependencia externa
            logger.warning("No se pudo cargar el template de sección: %s", exc)
            self._draw_section_schematic_legacy(document, context, box_left, box_bottom, box_width, box_top, reference_y, data)
            return

        if template.width <= 0 or template.height <= 0:
            self._draw_section_schematic_legacy(document, context, box_left, box_bottom, box_width, box_top, reference_y, data)
            return

        gap = 250.0
        schematic_bottom = reference_y + gap
        max_height = box_top - schematic_bottom - 150.0
        max_width = box_width - 400.0
        if max_height <= 0 or max_width <= 0:
            return

        scale = 0.7 * min(max_width / template.width, max_height / template.height)
        if scale <= 0:
            self._draw_section_schematic_legacy(document, context, box_left, box_bottom, box_width, box_top, reference_y, data)
            return

        target_width = template.width * scale
        target_left = box_left + (box_width - target_width) / 2.0
        offset = (
            target_left - template.min_x * scale,
            schematic_bottom - template.min_y * scale,
        )

        placeholders = self._section_placeholder_values(data)
        text_style = context.template.text_style("title")

        try:
            entities = template.instantiate(
                scale=scale,
                offset=offset,
                shape_layer=context.layer("title_block"),
                text_layer=context.layer("text"),
                text_style=text_style.name,
                placeholders=placeholders,
            )
        except Exception as exc:  # pragma: no cover - defensivo ante DXF inválido
            logger.warning("No se pudo instanciar el template de sección: %s", exc)
            self._draw_section_schematic_legacy(document, context, box_left, box_bottom, box_width, box_top, reference_y, data)
            return

        for entity in entities:
            document.add_entity(entity)

    def _section_placeholder_values(self, data):
        return {
            "BASE_VIGA": f"B = {data['base_mm'] / 1000:.2f} m",
            "ALTURA_VIGA": f"H = {data['height_mm'] / 1000:.2f} m",
            "BASE_ESTRIBO": f"b_e = {data['stirrup_width_mm'] / 1000:.2f} m",
            "ALTURA_ESTRIBO": f"h_e = {data['stirrup_height_mm'] / 1000:.2f} m",
            "GANCHO_ESTRIBO": f"Gancho {data['hook_type']}° - {data['stirrup_diameter']}",
            "RECUBRIMIENTO": f"Recubrimiento = {data['cover_mm'] / 10:.0f} cm",
        }

    def _draw_section_schematic_legacy(
        self,
        document,
        context,
        box_left,
        box_bottom,
        box_width,
        box_top,
        reference_y,
        data,
    ):
        data = data or self._section_schematic_data(context)
        base_mm = data["base_mm"]
        height_mm = data["height_mm"]
        if base_mm <= 0 or height_mm <= 0:
            return
        gap = 250.0
        schematic_bottom = reference_y + gap
        max_height = box_top - schematic_bottom - 150.0
        max_width = box_width - 400.0
        if max_height <= 0 or max_width <= 0:
            return
        scale = 0.7 * min(max_width / base_mm, max_height / height_mm)
        if scale <= 0:
            return
        section_width = base_mm * scale
        section_height = height_mm * scale
        section_left = box_left + (box_width - section_width) / 2.0
        section_bottom = schematic_bottom
        section_top = section_bottom + section_height

        def rect_points(left, bottom, width, height):
            return [
                (left, bottom),
                (left + width, bottom),
                (left + width, bottom + height),
                (left, bottom + height),
                (left, bottom),
            ]

        def circle_points(cx, cy, radius, segments=12):
            return [
                (
                    cx + radius * math.cos(2 * math.pi * i / segments),
                    cy + radius * math.sin(2 * math.pi * i / segments),
                )
                for i in range(segments + 1)
            ]

        text_layer = context.layer("text")
        text_style = context.template.text_style("title")
        text_height = context.text_height_mm * 0.9
        shape_layer = context.layer("title_block")

        document.add_entity(
            PolylineEntity(
                layer=shape_layer,
                points=rect_points(section_left, section_bottom, section_width, section_height),
            )
        )

        stirrup_width = data["stirrup_width_mm"] * scale
        stirrup_height = data["stirrup_height_mm"] * scale
        stirrup_left = section_left + (section_width - stirrup_width) / 2.0
        stirrup_bottom = section_bottom + (section_height - stirrup_height) / 2.0
        document.add_entity(
            PolylineEntity(
                layer=shape_layer,
                points=rect_points(stirrup_left, stirrup_bottom, stirrup_width, stirrup_height),
            )
        )

        bar_radius = max(5.0, 12.0 * scale)
        bar_points = [
            (stirrup_left + bar_radius, stirrup_bottom + bar_radius),
            (stirrup_left + stirrup_width - bar_radius, stirrup_bottom + bar_radius),
            (stirrup_left + bar_radius, stirrup_bottom + stirrup_height - bar_radius),
            (stirrup_left + stirrup_width - bar_radius, stirrup_bottom + stirrup_height - bar_radius),
        ]
        for (cx, cy) in bar_points:
            document.add_entity(
                PolylineEntity(
                    layer=shape_layer,
                    points=circle_points(cx, cy, bar_radius),
                )
            )

        diag_points = [
            (section_left + section_width * 0.55, section_bottom + section_height * 0.65),
            (section_left + section_width * 0.7, section_bottom + section_height * 0.8),
            (section_left + section_width * 0.75, section_bottom + section_height * 0.6),
            (section_left + section_width * 0.6, section_bottom + section_height * 0.45),
        ]
        document.add_entity(
            PolylineEntity(
                layer=shape_layer,
                points=diag_points,
            )
        )

        diag_points_2 = [
            (section_left + section_width * 0.65, section_bottom + section_height * 0.4),
            (section_left + section_width * 0.85, section_bottom + section_height * 0.55),
            (section_left + section_width * 0.9, section_bottom + section_height * 0.35),
            (section_left + section_width * 0.7, section_bottom + section_height * 0.2),
        ]
        document.add_entity(
            PolylineEntity(
                layer=shape_layer,
                points=diag_points_2,
            )
        )

        top_label = (section_left + section_width / 2.0, section_top + 120.0)
        left_label = (section_left - 80.0, section_bottom + section_height / 2.0)
        document.add_entity(
            TextEntity(
                layer=text_layer,
                content=f"B = {data['base_mm'] / 1000:.2f} m",
                insert=top_label,
                height=text_height,
                style=text_style.name,
                metadata={"halign": 1, "align_point": top_label},
            )
        )
        document.add_entity(
            TextEntity(
                layer=text_layer,
                content=f"H = {data['height_mm'] / 1000:.2f} m",
                insert=left_label,
                height=text_height,
                style=text_style.name,
                metadata={"halign": 2, "align_point": left_label},
            )
        )

        cover_label = (section_left + section_width / 2.0, stirrup_bottom - 120.0)
        document.add_entity(
            TextEntity(
                layer=text_layer,
                content=f"Recubrimiento = {data['cover_mm'] / 10:.0f} cm",
                insert=cover_label,
                height=text_height * 0.9,
                style=text_style.name,
                metadata={"halign": 1, "align_point": cover_label},
            )
        )

        stirrup_label = (section_left + section_width / 2.0, stirrup_bottom + stirrup_height / 2.0)
        document.add_entity(
            TextEntity(
                layer=text_layer,
                content=(
                    f"Estribo = {data['stirrup_width_mm'] / 1000:.2f} m x {data['stirrup_height_mm'] / 1000:.2f} m"
                ),
                insert=stirrup_label,
                height=text_height * 0.8,
                style=text_style.name,
                metadata={"halign": 1, "align_point": stirrup_label},
            )
        )

        hook_width = data["stirrup_width_mm"] * scale * 0.8
        hook_height = data["stirrup_height_mm"] * scale * 0.9
        hook_left = section_left + section_width + 120.0
        hook_bottom = section_bottom + section_height * 0.1
        hook_points = [
            (hook_left, hook_bottom),
            (hook_left + hook_width, hook_bottom),
            (hook_left + hook_width, hook_bottom + hook_height * 0.6),
            (hook_left + hook_width * 0.7, hook_bottom + hook_height * 0.8),
            (hook_left + hook_width * 0.9, hook_bottom + hook_height),
            (hook_left + hook_width * 0.6, hook_bottom + hook_height),
            (hook_left + hook_width * 0.2, hook_bottom + hook_height * 0.6),
            (hook_left + hook_width * 0.2, hook_bottom),
        ]
        document.add_entity(
            PolylineEntity(
                layer=shape_layer,
                points=hook_points,
            )
        )

        hook_label = (hook_left + hook_width / 2.0, hook_bottom + hook_height + 120.0)
        document.add_entity(
            TextEntity(
                layer=text_layer,
                content=f"Gancho {data['hook_type']}° - {data['stirrup_diameter']}",
                insert=hook_label,
                height=text_height * 0.85,
                style=text_style.name,
                metadata={"halign": 1, "align_point": hook_label},
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
