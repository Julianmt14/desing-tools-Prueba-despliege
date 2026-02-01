"""Utilidades compartidas para el diseño de estribos NSR-10."""

from .utils import (
    DEFAULT_STIRRUP_DIAMETER,
    DEFAULT_STIRRUP_HOOK_TYPE,
    calculate_effective_depth,
    calculate_spacing_for_zone,
    get_default_stirrup_spec,
    derive_confined_segments,
    derive_unconfined_segments,
    extract_splice_segments,
)

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
