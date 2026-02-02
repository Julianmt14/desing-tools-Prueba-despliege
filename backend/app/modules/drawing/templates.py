from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
import json
from functools import lru_cache
from typing import Any, Dict

from app.modules.drawing.schemas import DrawingUnits


@dataclass(slots=True)
class LayerStyle:
    name: str
    color: int = 7
    lineweight: float = 0.25
    linetype: str = "Continuous"


@dataclass(slots=True)
class TextStyle:
    name: str
    height: float = 2.5
    font: str = "simplex.shx"


@dataclass(slots=True)
class TemplateConfig:
    key: str
    locale: str
    units: DrawingUnits
    layers: Dict[str, LayerStyle] = field(default_factory=dict)
    text_styles: Dict[str, TextStyle] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    cover_cm_override: int | None = None

    def layer_name(self, alias: str, default: str | None = None) -> str:
        style = self.layers.get(alias)
        if style:
            return style.name
        return default or alias

    def layer_style(self, alias: str) -> LayerStyle | None:
        return self.layers.get(alias)

    def text_style(self, alias: str, fallback: str | None = None) -> TextStyle:
        style = self.text_styles.get(alias)
        if style:
            return style
        if fallback:
            return self.text_styles.get(fallback, TextStyle(name=fallback))
        return TextStyle(name="Standard")

    def cover_cm(self, fallback_cover_cm: int) -> int:
        return self.cover_cm_override or fallback_cover_cm


DEFAULT_UNITS = DrawingUnits(source_unit="m", target_unit="mm", scale_factor=1000.0, precision=2)
DEFAULT_LAYERS = {
    "beam_outline": LayerStyle(name="C-VIGA", color=7, lineweight=0.50),
    "beam_hatch": LayerStyle(name="C-VIGA-HATCH", color=7, lineweight=0.10),
    "supports": LayerStyle(name="C-APOYO", color=8, lineweight=0.35),
    "axes": LayerStyle(name="C-EJES", color=5, lineweight=0.18, linetype="CENTER"),
    "rebar_main": LayerStyle(name="A-REB-MAIN", color=1, lineweight=0.35),
    "rebar_stirrups": LayerStyle(name="A-REB-EST", color=3, lineweight=0.25),
    "dimensions": LayerStyle(name="C-COTAS", color=4, lineweight=0.18),
    "text": LayerStyle(name="C-TEXT", color=7, lineweight=0.18),
    "title_block": LayerStyle(name="A-CART", color=7, lineweight=0.25),
}

DEFAULT_TEXT_STYLES = {
    "labels": TextStyle(name="T-LABELS", height=3.0),
    "dimensions": TextStyle(name="T-DIMS", height=2.5),
    "title": TextStyle(name="T-TITLE", height=4.0),
}

DEFAULT_TEMPLATE = TemplateConfig(
    key="beam/default",
    locale="es-CO",
    units=DEFAULT_UNITS,
    layers=DEFAULT_LAYERS,
    text_styles=DEFAULT_TEXT_STYLES,
    metadata={
        "title_block_label": "DESPIECE DE VIGA",
        "notes": ["Norma NSR-10", "fc' y fy según especificación"],
    },
    cover_cm_override=None,
)

TEMPLATES: Dict[str, TemplateConfig] = {
    DEFAULT_TEMPLATE.key: DEFAULT_TEMPLATE,
}


def get_template_config(template_key: str | None) -> TemplateConfig:
    manifest = _load_manifest()
    if template_key and template_key in manifest:
        return manifest[template_key]
    return manifest[DEFAULT_TEMPLATE.key]


@lru_cache()
def _load_manifest() -> Dict[str, TemplateConfig]:
    template_map: Dict[str, TemplateConfig] = {DEFAULT_TEMPLATE.key: DEFAULT_TEMPLATE}
    try:
        with resources.files("app.modules.drawing").joinpath("templates_manifest.json").open("r", encoding="utf-8") as fp:
            raw_manifest = json.load(fp)
    except FileNotFoundError:
        return template_map

    for entry in raw_manifest.get("templates", []):
        key = entry["key"]
        locale = entry.get("locale", DEFAULT_TEMPLATE.locale)
        units = DrawingUnits(**entry.get("units", DEFAULT_TEMPLATE.units.model_dump()))
        layer_defs = {
            alias: LayerStyle(**data)
            for alias, data in entry.get("layers", {}).items()
        }
        text_defs = {
            alias: TextStyle(**data)
            for alias, data in entry.get("text_styles", {}).items()
        }
        template_map[key] = TemplateConfig(
            key=key,
            locale=locale,
            units=units,
            layers=layer_defs or DEFAULT_LAYERS,
            text_styles=text_defs or DEFAULT_TEXT_STYLES,
            metadata=entry.get("metadata", {}),
            cover_cm_override=entry.get("cover_cm_override"),
        )
    return template_map


def list_templates() -> list[dict[str, Any]]:
    manifest = _load_manifest()
    templates = []
    for template in manifest.values():
        templates.append(
            {
                "key": template.key,
                "locale": template.locale,
                "metadata": template.metadata,
                "cover_cm_override": template.cover_cm_override,
            }
        )
    return templates


__all__ = [
    "LayerStyle",
    "TemplateConfig",
    "TextStyle",
    "get_template_config",
    "list_templates",
]
