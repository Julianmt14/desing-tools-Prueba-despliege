from __future__ import annotations

from dataclasses import dataclass

from app.modules.drawing.domain import PolylineEntity, TextEntity


@dataclass(slots=True)
class TitleBlockConfig:
    width_mm: float = 220.0
    height_mm: float = 90.0
    margin_mm: float = 35.0


class TitleBlockRenderer:
    def __init__(self, config: TitleBlockConfig | None = None) -> None:
        self.config = config or TitleBlockConfig()

    def draw(self, document, context) -> None:
        layer = context.layer("title_block")
        style = context.layer_style("title_block")
        text_style = context.template.text_style("title")

        origin_x = context.origin[0] + self.config.margin_mm
        origin_y = context.origin[1] - self.config.height_mm - self.config.margin_mm
        block_points = [
            (origin_x, origin_y),
            (origin_x + self.config.width_mm, origin_y),
            (origin_x + self.config.width_mm, origin_y + self.config.height_mm),
            (origin_x, origin_y + self.config.height_mm),
            (origin_x, origin_y),
        ]

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
        lines = [
            context.template.metadata.get("title_block_label", "DESPIECE"),
            f"Proyecto: {metadata.project_name}",
            f"Viga: {metadata.beam_label}",
            f"Nivel: {metadata.element_level if metadata.element_level is not None else 'N/A'}",
        ]

        cursor_y = origin_y + self.config.height_mm - 15.0
        for line in lines:
            document.add_entity(
                TextEntity(
                    layer=context.layer("text"),
                    content=line,
                    insert=(origin_x + 10.0, cursor_y),
                    height=text_style.height,
                    style=text_style.name,
                )
            )
            cursor_y -= 12.0


__all__ = ["TitleBlockRenderer", "TitleBlockConfig"]
