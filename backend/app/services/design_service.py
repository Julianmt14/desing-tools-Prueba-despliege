from __future__ import annotations

import logging
import re
from collections import Counter
from decimal import Decimal
from typing import Any, Iterable, Literal, Sequence, cast

from sqlalchemy.orm import Session, selectinload

from app import models
from app.modules.drawing.schemas import (
    AxisMarker,
    BeamDrawingMetadata,
    BeamDrawingPayload,
    BeamGeometry,
    BeamRebarLayout,
    BeamSpan,
    BeamSupport,
    DrawingUnits,
    RebarGroup,
)
from app.schemas.design import (
    DespieceVigaCreate,
    DespieceVigaRead,
    DespieceVigaUpdate,
    DesignCreate,
    SegmentReinforcement,
    StirrupConfig,
)
from app.schemas.tools.despiece import DetailingResults


logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


_LENGTH_PATTERN = re.compile(r"([0-9]+(?:[.,][0-9]+)?)")
DEFAULT_SUPPORT_WIDTH_CM = 35.0
RebarPosition = Literal["top", "bottom"]


def _attach_despiece(design: models.Design, despiece_data: DespieceVigaCreate | None) -> None:
    if despiece_data is None:
        return

    if design.beam_despiece is None:
        design.beam_despiece = models.DespieceViga(**despiece_data.model_dump())
    else:
        for key, value in despiece_data.model_dump().items():
            setattr(design.beam_despiece, key, value)


def create_design(db: Session, *, design_in: DesignCreate, user_id: int) -> models.Design:
    payload = design_in.model_dump(exclude={"despiece_viga"})
    design = models.Design(**payload, user_id=user_id)
    _attach_despiece(design, design_in.despiece_viga)
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


def list_designs(db: Session, *, user_id: int) -> list[models.Design]:
    return (
        db.query(models.Design)
        .options(selectinload(models.Design.beam_despiece))
        .filter(models.Design.user_id == user_id)
        .all()
    )


def get_design(db: Session, *, design_id: int, user_id: int) -> models.Design | None:
    return (
        db.query(models.Design)
        .options(selectinload(models.Design.beam_despiece))
        .filter(models.Design.id == design_id, models.Design.user_id == user_id)
        .first()
    )


def update_despiece_for_design(
    db: Session,
    *,
    design_id: int,
    user_id: int,
    despiece_in: DespieceVigaUpdate,
) -> models.DespieceViga | None:
    design = get_design(db, design_id=design_id, user_id=user_id)
    if design is None:
        return None

    data = despiece_in.model_dump(exclude_unset=True)
    if not data:
        return design.beam_despiece

    if design.beam_despiece is None:
        design.beam_despiece = models.DespieceViga(design_id=design.id)

    for key, value in data.items():
        setattr(design.beam_despiece, key, value)

    db.add(design)
    db.commit()
    db.refresh(design.beam_despiece)
    return design.beam_despiece


def delete_despiece_for_design(db: Session, *, design_id: int, user_id: int) -> bool:
    design = get_design(db, design_id=design_id, user_id=user_id)
    if design is None or design.beam_despiece is None:
        return False

    db.delete(design.beam_despiece)
    db.commit()
    return True


def build_beam_drawing_payload(design: models.Design) -> BeamDrawingPayload:
    """Genera el payload normalizado que consumirá el módulo de graficación."""

    if design.beam_despiece is None:
        raise ValueError("El diseño no tiene un despiece de viga asociado")

    despiece = design.beam_despiece
    despiece_schema = DespieceVigaRead.model_validate(despiece)
    detailing_results = _load_detailing_results(despiece.detailing_results)

    supports = _build_supports(despiece_schema)
    spans = _build_spans(despiece_schema, supports)
    axis_markers = _build_axis_markers(supports)

    total_length = _resolve_total_length(despiece_schema, supports, spans)
    geometry = BeamGeometry(
        total_length_m=total_length,
        spans=spans,
        supports=supports,
        axis_markers=axis_markers,
        has_cantilevers=despiece_schema.has_cantilevers,
    )

    axis_labels = [marker.label for marker in axis_markers]
    metadata = BeamDrawingMetadata(
        project_name=despiece_schema.project_name,
        beam_label=despiece_schema.beam_label,
        element_identifier=despiece_schema.element_identifier,
        element_level=_safe_float(despiece_schema.element_level),
        element_quantity=despiece_schema.element_quantity,
        axis_labels=axis_labels,
        notes=despiece_schema.notes,
        concrete_strength=despiece_schema.concrete_strength,
        reinforcement=despiece_schema.reinforcement,
        energy_dissipation_class=despiece_schema.energy_dissipation_class,
        updated_at=despiece_schema.updated_at,
    )

    rebar_layout = _build_rebar_layout(despiece_schema)
    stirrups_config = _parse_stirrups_config(despiece_schema.stirrups_config)

    design_id = int(getattr(design, "id") or 0)
    despiece_id = int(getattr(despiece, "id") or 0)

    return BeamDrawingPayload(
        design_id=design_id,
        despiece_id=despiece_id,
        metadata=metadata,
        geometry=geometry,
        rebar_layout=rebar_layout,
        detailing_results=detailing_results,
        stirrups_config=stirrups_config,
        drawing_units=DrawingUnits(
            source_unit="m",
            target_unit="mm",
            scale_factor=1000.0,
            precision=2,
        ),
    )


def _load_detailing_results(raw_results: dict | None) -> DetailingResults | None:
    if not raw_results:
        return None

    try:
        return DetailingResults.model_validate(raw_results)
    except Exception as exc:  # pragma: no cover - defensiva
        logger.warning("No fue posible validar detailing_results: %s", exc)
        return None


def _build_supports(despiece: DespieceVigaRead) -> list[BeamSupport]:
    span_data = despiece.span_geometries or []
    expected_supports = len(span_data) + 1
    widths_cm = list(despiece.support_widths_cm or [])

    if len(widths_cm) < expected_supports:
        missing = expected_supports - len(widths_cm)
        widths_cm.extend([widths_cm[-1] if widths_cm else DEFAULT_SUPPORT_WIDTH_CM] * missing)

    axis_labels = _axis_labels(despiece.axis_numbering, expected_supports)

    supports: list[BeamSupport] = []
    cursor = 0.0

    for index in range(expected_supports):
        width_cm = widths_cm[index] if index < len(widths_cm) else DEFAULT_SUPPORT_WIDTH_CM
        width_m = round((width_cm or DEFAULT_SUPPORT_WIDTH_CM) / 100.0, 4)
        start = round(cursor, 4)
        end = round(cursor + width_m, 4)

        supports.append(
            BeamSupport(
                index=index,
                label=axis_labels[index],
                width_m=width_m,
                start_m=start,
                end_m=end,
            )
        )

        cursor = end
        if index < len(span_data):
            span_length = _span_length(span_data[index])
            cursor = round(cursor + span_length, 4)

    return supports


def _build_spans(
    despiece: DespieceVigaRead,
    supports: Sequence[BeamSupport],
) -> list[BeamSpan]:
    span_dicts = despiece.span_geometries or []
    spans: list[BeamSpan] = []

    for idx, span in enumerate(span_dicts):
        start_support = supports[idx]
        end_support = supports[idx + 1]
        start = round(start_support.end_m, 4)
        clear_length = _span_length(span)
        end = round(start + clear_length, 4)

        spans.append(
            BeamSpan(
                index=idx,
                label=span.get("label") or f"Luz {idx + 1}",
                start_support_index=start_support.index,
                end_support_index=end_support.index,
                clear_length_m=clear_length,
                start_m=start,
                end_m=end,
                section_width_cm=_span_width(span),
                section_height_cm=_span_height(span),
            )
        )

    return spans


def _build_axis_markers(supports: Sequence[BeamSupport]) -> list[AxisMarker]:
    markers: list[AxisMarker] = []
    for support in supports:
        position = round(support.start_m + (support.width_m / 2.0), 4)
        markers.append(
            AxisMarker(
                index=support.index,
                label=support.label,
                position_m=position,
            )
        )
    return markers


def _resolve_total_length(
    despiece: DespieceVigaRead,
    supports: Sequence[BeamSupport],
    spans: Sequence[BeamSpan],
) -> float:
    if despiece.beam_total_length_m and despiece.beam_total_length_m > 0:
        return float(despiece.beam_total_length_m)

    if supports:
        return round(supports[-1].end_m, 4)

    if spans:
        return round(spans[-1].end_m, 4)

    return 0.0


def _build_rebar_layout(despiece: DespieceVigaRead) -> BeamRebarLayout:
    max_length = _parse_length_string(despiece.max_rebar_length_m, default=12.0)

    top_groups = _group_rebars(
        despiece.top_bar_diameters,
        despiece.top_bars_qty,
        position="top",
    )
    bottom_groups = _group_rebars(
        despiece.bottom_bar_diameters,
        despiece.bottom_bars_qty,
        position="bottom",
    )

    segment_reinf = _parse_segment_reinforcements(despiece.segment_reinforcements)

    return BeamRebarLayout(
        top_groups=top_groups,
        bottom_groups=bottom_groups,
        hook_type=despiece.hook_type,
        cover_cm=despiece.cover_cm,
        lap_splice_length_min_m=despiece.lap_splice_length_min_m,
        max_rebar_length_m=max_length,
        segment_reinforcements=segment_reinf,
    )


def _parse_stirrups_config(
    data: Iterable[StirrupConfig | dict[str, Any]] | None,
) -> list[StirrupConfig] | None:
    if not data:
        return None

    parsed: list[StirrupConfig] = []
    for item in data:
        if isinstance(item, StirrupConfig):
            parsed.append(item)
        else:
            parsed.append(StirrupConfig.model_validate(item))
    return parsed


def _parse_segment_reinforcements(
    data: Iterable[dict] | None,
) -> list[SegmentReinforcement] | None:
    if not data:
        return None
    return [SegmentReinforcement.model_validate(item) for item in data]


def _group_rebars(
    diameters: Iterable[str] | None,
    fallback_quantity: int,
    *,
    position: RebarPosition,
) -> list[RebarGroup]:
    cleaned = [diam for diam in (diameters or []) if diam]
    if cleaned:
        counts = Counter(cleaned)
        return [
            RebarGroup(diameter=diam, quantity=count, position=position)
            for diam, count in counts.items()
        ]

    if fallback_quantity:
        placeholder = "N/D"
        note = "Diámetro no especificado en el formulario"
        return [
            RebarGroup(
                diameter=placeholder,
                quantity=fallback_quantity,
                position=position,
                notes=note,
            )
        ]

    return []


def _parse_length_string(raw_value: str | None, default: float) -> float:
    if not raw_value:
        return default
    match = _LENGTH_PATTERN.search(raw_value)
    if not match:
        return default
    return float(match.group(1).replace(",", "."))


def _span_length(span: dict) -> float:
    value = span.get("clear_span_between_supports_m")
    if value is None:
        value = span.get("length_m")
    return round(float(value or 0.0), 4)


def _span_width(span: dict) -> float:
    value = span.get("base_cm") or span.get("section_width_cm") or span.get("width_cm")
    return float(value or 30.0)


def _span_height(span: dict) -> float:
    value = span.get("height_cm") or span.get("section_height_cm")
    return float(value or 45.0)


def _safe_float(value: float | Decimal | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _axis_labels(axis_numbering: str | None, expected: int) -> list[str]:
    if axis_numbering:
        raw_tokens = re.split(r"[-,\s]+", axis_numbering)
        labels = [token for token in raw_tokens if token]
        if len(labels) >= expected:
            return labels[:expected]

    return [f"EJE {index + 1}" for index in range(expected)]
