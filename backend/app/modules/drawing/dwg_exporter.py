from __future__ import annotations

import importlib
import logging
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any, Sequence

_EZDXF_MODULE: Any | None = None
_DXF_UNITS: Any | None = None
LINEWEIGHT_MAP: dict[float, int] = {}
logger = logging.getLogger(__name__)


def _ensure_ezdxf():
    global _EZDXF_MODULE, _DXF_UNITS, LINEWEIGHT_MAP
    if _EZDXF_MODULE is None or _DXF_UNITS is None:
        try:
            _EZDXF_MODULE = importlib.import_module("ezdxf")
            _DXF_UNITS = importlib.import_module("ezdxf.units")
            const_mod = importlib.import_module("ezdxf.lldxf.const")
            LINEWEIGHT_MAP = dict(getattr(const_mod, "LINEWEIGHT_TO_DXU", {}))
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("ezdxf no está instalado en el entorno actual") from exc
    return _EZDXF_MODULE, _DXF_UNITS

from app.modules.drawing.domain import (
    DimensionEntity,
    DrawingDocument,
    DrawingEntity,
    HatchEntity,
    LineEntity,
    PolylineEntity,
    TextEntity,
)
from app.modules.drawing.templates import TemplateConfig, get_template_config

EXPORT_DIR = Path(os.getenv("DRAWING_EXPORT_DIR", Path(tempfile.gettempdir()) / "exports"))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class DWGExporter:
    def __init__(self, *, version: str = "R2018") -> None:
        self.version = version

    def export(
        self,
        document: DrawingDocument,
        filename: str | None = None,
        output_dir: Path | None = None,
    ) -> Path:
        ezdxf_mod, dxf_units_mod = _ensure_ezdxf()
        target_dir = Path(output_dir) if output_dir else EXPORT_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_name = filename or f"drawing_{document.metadata.get('beam', {}).get('beam_label', 'beam')}.dxf"
        target_path = target_dir / safe_name

        dxf_doc = ezdxf_mod.new(self.version)
        dxf_doc.units = dxf_units_mod.MM
        template = self._resolve_template(document)
        self._configure_layers(dxf_doc, document, template)
        self._configure_text_styles(dxf_doc, document, template)
        msp = dxf_doc.modelspace()

        for entity in document.entities:
            self._add_entity(msp, entity, template)

        requested_suffix = target_path.suffix.lower()
        dxf_target = target_path if requested_suffix == ".dxf" else target_path.with_suffix(".dxf")
        dxf_doc.saveas(dxf_target)

        if requested_suffix == ".dwg":
            try:  # pragma: no cover - depende de ODA File Converter
                odafc = importlib.import_module("ezdxf.addons.odafc")
                odafc.export_dwg(dxf_doc, target_path, replace=True)
                if dxf_target != target_path:
                    with suppress(OSError):
                        dxf_target.unlink()
                return target_path
            except Exception as exc:  # pragma: no cover - runtime only
                logger.warning("No se pudo convertir el DXF a DWG (%s); se entregará DXF", exc)
        return dxf_target

    def _add_entity(self, msp, entity: DrawingEntity, template: TemplateConfig | None) -> None:
        if isinstance(entity, PolylineEntity):
            msp.add_lwpolyline(entity.points, format="xy", dxfattribs=self._attribs(entity))
        elif isinstance(entity, LineEntity):
            msp.add_line(entity.start, entity.end, dxfattribs=self._attribs(entity))
        elif isinstance(entity, TextEntity):
            msp.add_text(
                entity.content,
                height=entity.height,
                dxfattribs={
                    "layer": entity.layer,
                    "style": entity.style,
                    "rotation": entity.rotation,
                    "insert": entity.insert,
                },
            )
        elif isinstance(entity, HatchEntity):
            hatch = msp.add_hatch(color=7, dxfattribs={"layer": entity.layer})
            if entity.pattern.upper() == "SOLID":
                hatch.set_solid_fill(color=7)
            else:
                hatch.set_pattern_fill(
                    entity.pattern,
                    color=7,
                    angle=entity.rotation,
                    scale=entity.scale,
                )
                hatch.dxf.pattern_scale = entity.scale
            hatch.paths.add_polyline_path(entity.boundary, is_closed=True)
        elif isinstance(entity, DimensionEntity):
            msp.add_line(entity.start, entity.end, dxfattribs=self._attribs(entity))
            if entity.text_override:
                mid_x = (entity.start[0] + entity.end[0]) / 2
                mid_y = (entity.start[1] + entity.end[1]) / 2 + 2.0
                dim_text_style = template.text_style("dimensions") if template else None
                text_height = entity.metadata.get("text_height")
                if text_height is None and dim_text_style:
                    text_height = dim_text_style.height
                if text_height is None:
                    text_height = entity.metadata.get("text_height", 5.0)
                msp.add_text(
                    entity.text_override,
                    height=text_height,
                    dxfattribs={
                        "layer": entity.layer,
                        "rotation": 0.0,
                        "style": dim_text_style.name if dim_text_style else "Standard",
                        "insert": (mid_x, mid_y),
                    },
                )

    def _configure_layers(self, dxf_doc, document: DrawingDocument, template: TemplateConfig | None) -> None:
        if template:
            for style in template.layers.values():
                if style.name not in dxf_doc.layers:
                    dxf_doc.layers.add(name=style.name, color=style.color)
        for entity in document.entities:
            layer = entity.layer
            if layer not in dxf_doc.layers:
                dxf_doc.layers.add(name=layer, color=7)

    def _configure_text_styles(self, dxf_doc, document: DrawingDocument, template: TemplateConfig | None) -> None:
        if template:
            for style in template.text_styles.values():
                self._ensure_text_style(dxf_doc, style.name, style.font)
        for entity in document.entities:
            if isinstance(entity, TextEntity):
                self._ensure_text_style(dxf_doc, entity.style or "Standard", None)

    def _ensure_text_style(self, dxf_doc, name: str, font: str | None) -> None:
        if not name or name in dxf_doc.styles:
            return
        if font:
            dxf_doc.styles.add(name, font=font)
        else:
            dxf_doc.styles.add(name)

    def _resolve_template(self, document: DrawingDocument) -> TemplateConfig | None:
        metadata = document.metadata or {}
        template_key = metadata.get("template")
        try:
            return get_template_config(template_key)
        except Exception:  # pragma: no cover - fallback defensivo
            logger.warning("No se pudo cargar el template %s, se usará None", template_key)
            return None

    def _attribs(self, entity) -> dict:
        attribs = {"layer": entity.layer}
        if getattr(entity, "color", None):
            attribs["color"] = entity.color
        if getattr(entity, "lineweight", None) and LINEWEIGHT_MAP:
            attribs["lineweight"] = LINEWEIGHT_MAP.get(entity.lineweight, 25)
        return attribs


__all__ = ["DWGExporter", "EXPORT_DIR"]
