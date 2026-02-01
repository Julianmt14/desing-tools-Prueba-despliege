"""Funciones utilitarias para definir estribos según NSR-10."""

from __future__ import annotations

from collections.abc import Iterable
from typing import List, Literal, Sequence, Tuple

from app.schemas.tools.despiece import ProhibitedZone, RebarDetail

DEFAULT_STIRRUP_DIAMETER = "#3"
DEFAULT_STIRRUP_HOOK_TYPE = "135"
_INNER_CLEARANCE_CM = 2.0

ZoneType = Literal["confined", "non_confined"]



def calculate_effective_depth(section_height_cm: float, cover_cm: float) -> float:
    """Retorna d (m), definido como alto - recubrimiento - 2 cm."""
    height_cm = max(section_height_cm or 0.0, 0.0)
    cover_value_cm = max(cover_cm or 0.0, 0.0)
    effective_depth_cm = max(height_cm - cover_value_cm - _INNER_CLEARANCE_CM, 0.0)
    return effective_depth_cm / 100.0


def calculate_spacing_for_zone(effective_depth_m: float, zone: ZoneType) -> float:
    factor = 0.25 if zone == "confined" else 0.5
    return max(0.0, effective_depth_m * factor)


def get_default_stirrup_spec(section_height_cm: float, cover_cm: float) -> dict:
    effective_depth_m = calculate_effective_depth(section_height_cm, cover_cm)
    return {
        "diameter": DEFAULT_STIRRUP_DIAMETER,
        "hook_type": DEFAULT_STIRRUP_HOOK_TYPE,
        "spacing_confined_m": calculate_spacing_for_zone(effective_depth_m, "confined"),
        "spacing_non_confined_m": calculate_spacing_for_zone(effective_depth_m, "non_confined"),
    }


def merge_segments(segments: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    sanitized = [(min(a, b), max(a, b)) for a, b in segments if a is not None and b is not None]
    sanitized = [(start, end) for start, end in sanitized if end > start]
    if not sanitized:
        return []
    sanitized.sort(key=lambda seg: seg[0])
    merged: List[Tuple[float, float]] = []
    current_start, current_end = sanitized[0]
    for start, end in sanitized[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
            continue
        merged.append((current_start, current_end))
        current_start, current_end = start, end
    merged.append((current_start, current_end))
    return merged


def derive_confined_segments(
    prohibited_zones: Sequence[ProhibitedZone] | None,
    lap_splices: Sequence[Tuple[float, float]] | None,
) -> List[Tuple[float, float]]:
    segments: List[Tuple[float, float]] = []
    for zone in prohibited_zones or []:
        description = (zone.description or "").lower()
        if zone.support_index is None:
            continue
        if "dentro del apoyo" in description:
            continue
        segments.append((zone.start_m, zone.end_m))
    if lap_splices:
        segments.extend(lap_splices)
    return merge_segments(segments)


def derive_unconfined_segments(
    total_length: float,
    confined_segments: Sequence[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    if total_length <= 0:
        return []
    merged_confined = merge_segments(confined_segments)
    segments: List[Tuple[float, float]] = []
    cursor = 0.0
    for start, end in merged_confined:
        if start > cursor:
            segments.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < total_length:
        segments.append((cursor, total_length))
    return [(start, end) for start, end in segments if end > start]


def extract_splice_segments(rebars: Iterable[RebarDetail | dict]) -> List[Tuple[float, float]]:
    segments: List[Tuple[float, float]] = []
    for bar in rebars or []:
        splices = getattr(bar, "splices", None)
        if splices is None and isinstance(bar, dict):
            splices = bar.get("splices")
        if not isinstance(splices, Iterable):  # type: ignore[arg-type]
            continue
        for splice in splices:
            if splice is None:
                continue
            start = splice.get("start") if isinstance(splice, dict) else getattr(splice, "start", None)
            end = splice.get("end") if isinstance(splice, dict) else getattr(splice, "end", None)
            if start is None or end is None:
                continue
            if end <= start:
                continue
            segments.append((float(start), float(end)))
    return merge_segments(segments)

__all__ = [
    "DEFAULT_STIRRUP_DIAMETER",
    "DEFAULT_STIRRUP_HOOK_TYPE",
    "calculate_effective_depth",
    "calculate_spacing_for_zone",
    "get_default_stirrup_spec",
    "derive_confined_segments",
    "derive_unconfined_segments",
    "extract_splice_segments",
]
