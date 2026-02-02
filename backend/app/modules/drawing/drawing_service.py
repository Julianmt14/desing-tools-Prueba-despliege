from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass

from app.modules.drawing.beam_renderer import BeamRenderer
from app.modules.drawing.dimensions import DimensionRenderer
from app.modules.drawing.domain import DrawingDocument, DrawingEntity
from app.modules.drawing.geometry import CoordinateSpace, to_drawing_units
from app.modules.drawing.rebar_drawer import RebarDrawer
from app.modules.drawing.schemas import BeamDrawingPayload, DrawingExportRequest
from app.modules.drawing.templates import TemplateConfig, get_template_config
from app.modules.drawing.title_block import TitleBlockRenderer


@dataclass(slots=True)
class RenderContext:
    payload: BeamDrawingPayload
    template: TemplateConfig
    space: CoordinateSpace
    beam_height_mm: float
    cover_mm: float
    locale: str
    origin: tuple[float, float] = (0.0, 0.0)

    def layer(self, alias: str) -> str:
        return self.template.layer_name(alias, alias)

    def layer_style(self, alias: str):
        return self.template.layer_style(alias)


class BeamDrawingService:
    def __init__(
        self,
        *,
        template_key: str | None = "beam/default",
        scale: float = 50.0,
    ) -> None:
        self.template_key = template_key or "beam/default"
        self.scale = scale
        self.beam_renderer = BeamRenderer()
        self.rebar_drawer = RebarDrawer()
        self.dimension_renderer = DimensionRenderer()
        self.title_block_renderer = TitleBlockRenderer()

    def render_document(
        self,
        payload: BeamDrawingPayload,
        *,
        template_override: str | None = None,
        locale: str | None = None,
        export_request: DrawingExportRequest | None = None,
    ) -> DrawingDocument:
        template_key = export_request.template if export_request else template_override or self.template_key
        template = get_template_config(template_key)
        render_locale = export_request.locale if export_request else locale or template.locale
        render_scale = export_request.scale if export_request else self.scale
        doc = DrawingDocument(
            units=payload.drawing_units,
            scale=render_scale,
            metadata={
                "template": template.key,
                "locale": render_locale,
                "beam": payload.metadata.model_dump(),
            },
        )
        space = CoordinateSpace(units=payload.drawing_units)
        context = RenderContext(
            payload=payload,
            template=template,
            space=space,
            beam_height_mm=self._beam_height_mm(payload, doc),
            cover_mm=self._cover_mm(payload, template, doc),
            locale=render_locale,
        )

        self.beam_renderer.draw(doc, context)
        self.rebar_drawer.draw(doc, context)
        self.dimension_renderer.draw(doc, context)
        self.title_block_renderer.draw(doc, context)
        return doc

    def _beam_height_mm(self, payload: BeamDrawingPayload, document: DrawingDocument) -> float:
        span_heights = [span.section_height_cm for span in payload.geometry.spans]
        max_height_cm = max(span_heights) if span_heights else 45.0
        return payload.drawing_units.scale_factor * (max_height_cm / 100.0)

    def _cover_mm(
        self,
        payload: BeamDrawingPayload,
        template: TemplateConfig,
        document: DrawingDocument,
    ) -> float:
        cover_cm = template.cover_cm(payload.rebar_layout.cover_cm)
        return payload.drawing_units.scale_factor * (cover_cm / 100.0)


def build_preview_payload(payload: BeamDrawingPayload, export_request: DrawingExportRequest | None = None) -> DrawingDocument:
    service = BeamDrawingService()
    return service.render_document(payload, export_request=export_request)


def serialize_document(document: DrawingDocument) -> dict:
    def serialize_entity(entity: DrawingEntity) -> dict:
        if is_dataclass(entity):
            data = asdict(entity)
        else:  # pragma: no cover - fallback defensive
            data = dict(entity)
        data["type"] = entity.__class__.__name__
        return data

    return {
        "units": document.units.model_dump(),
        "scale": document.scale,
        "metadata": document.metadata,
        "entities": [serialize_entity(entity) for entity in document.entities],
    }


__all__ = ["BeamDrawingService", "RenderContext", "build_preview_payload", "serialize_document"]
