"""Generate a schematic beam section with reinforcement callouts as SVG.

The script reads the current preview payload (same utilizado para `stirrups_preview`)
so the dimensions always match the beam being detailed.

Run:
    python -m scripts.section_schematic
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:  # Import dinámico para reutilizar el payload de previsualización
    from scripts.stirrups_preview import build_payload as build_preview_payload
except Exception:  # pragma: no cover - entorno sin script
    build_preview_payload = None

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "preview_outputs"
OUTPUT_FILE = OUTPUT_DIR / "section_schematic.svg"

BAR_RADIUS_M = 0.018


@dataclass(slots=True)
class SectionParameters:
    base_m: float = 0.30
    height_m: float = 0.45
    cover_m: float = 0.04
    stirrup_width_m: float = 0.22
    stirrup_height_m: float = 0.37
    hook_type: str = "135"
    stirrup_diameter: str = "#3"

    @property
    def stirrup_offset_x(self) -> float:
        return max((self.base_m - self.stirrup_width_m) / 2.0, 0.01)

    @property
    def stirrup_offset_y(self) -> float:
        return max((self.height_m - self.stirrup_height_m) / 2.0, 0.01)


def _extract_parameters() -> SectionParameters:
    params = SectionParameters()
    if build_preview_payload is None:
        return params

    try:
        payload = build_preview_payload()
    except Exception:
        return params

    geometry = getattr(payload, "geometry", None)
    if geometry and geometry.spans:
        span = geometry.spans[0]
        if getattr(span, "section_width_cm", None):
            params.base_m = float(span.section_width_cm) / 100.0
        if getattr(span, "section_height_cm", None):
            params.height_m = float(span.section_height_cm) / 100.0

    rebar_layout = getattr(payload, "rebar_layout", None)
    if rebar_layout and getattr(rebar_layout, "cover_cm", None):
        params.cover_m = float(rebar_layout.cover_cm) / 100.0

    detailing = getattr(payload, "detailing_results", None)
    summary = getattr(detailing, "stirrups_summary", None) if detailing else None
    if summary:
        params.hook_type = summary.hook_type or params.hook_type
        params.stirrup_diameter = summary.diameter or params.stirrup_diameter
        if summary.span_specs:
            spec = summary.span_specs[0]
            params.stirrup_width_m = float(spec.stirrup_width_cm) / 100.0
            params.stirrup_height_m = float(spec.stirrup_height_cm) / 100.0
            params.base_m = float(spec.base_cm) / 100.0
            params.height_m = float(spec.height_cm) / 100.0
            params.cover_m = float(spec.cover_cm) / 100.0

    if params.stirrup_width_m <= 0.0:
        params.stirrup_width_m = max(params.base_m - 2 * params.cover_m, params.base_m * 0.7)
    if params.stirrup_height_m <= 0.0:
        params.stirrup_height_m = max(params.height_m - 2 * params.cover_m, params.height_m * 0.7)

    return params


def _svg_rect(x, y, width, height, stroke="black", stroke_width=2, dash: str | None = None, fill="none") -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<rect x="{x:.3f}" y="{-y - height:.3f}" width="{width:.3f}" height="{height:.3f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{dash_attr}/>'
    )


def _svg_circle(cx, cy, r) -> str:
    return f'<circle cx="{cx:.3f}" cy="{-cy:.3f}" r="{r:.3f}" fill="none" stroke="black" stroke-width="1.5" />'


def _svg_polyline(points, stroke_width=2, stroke="black", fill="none") -> str:
    coords = " ".join(f"{x:.3f},{-y:.3f}" for (x, y) in points)
    return f'<polyline points="{coords}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" />'


def _svg_line(x1, y1, x2, y2, stroke_width=2, stroke="black") -> str:
    return f'<line x1="{x1:.3f}" y1="{-y1:.3f}" x2="{x2:.3f}" y2="{-y2:.3f}" stroke="{stroke}" stroke-width="{stroke_width}" />'


def _svg_text(x, y, text, size=12, anchor="middle", rotation=None, weight="normal") -> str:
    rotate_attr = f' transform="rotate({rotation},{x:.3f},{-y:.3f})"' if rotation else ""
    weight_attr = f' font-weight="{weight}"' if weight != "normal" else ""
    return (
        f'<text x="{x:.3f}" y="{-y:.3f}" font-size="{size}" '
        f'text-anchor="{anchor}" dominant-baseline="middle"{rotate_attr}{weight_attr}>{text}</text>'
    )


def _svg_arrow(x1, y1, x2, y2, text="", size=10):
    """Dibuja una línea con flecha y texto"""
    # Línea principal
    line = f'<line x1="{x1:.3f}" y1="{-y1:.3f}" x2="{x2:.3f}" y2="{-y2:.3f}" stroke="black" stroke-width="1.5"/>'
    
    # Flecha (triángulo simple)
    dx = x2 - x1
    dy = y2 - y1
    length = (dx**2 + dy**2)**0.5
    if length > 0:
        ux = dx / length
        uy = dy / length
        arrow_size = 0.03
        arrow_points = [
            (x2, y2),
            (x2 - arrow_size * ux - arrow_size * 0.5 * uy, y2 - arrow_size * uy + arrow_size * 0.5 * ux),
            (x2 - arrow_size * ux + arrow_size * 0.5 * uy, y2 - arrow_size * uy - arrow_size * 0.5 * ux)
        ]
        arrow_coords = " ".join(f"{p[0]:.3f},{-p[1]:.3f}" for p in arrow_points)
        arrow = f'<polygon points="{arrow_coords}" fill="black"/>'
    else:
        arrow = ""
    
    # Texto
    if text:
        text_x = (x1 + x2) / 2
        text_y = (y1 + y2) / 2
        # Ajustar posición del texto para que no esté sobre la línea
        offset = 0.02
        if abs(dx) > abs(dy):  # Línea más horizontal
            text_y -= offset
        else:  # Línea más vertical
            text_x += offset
        
        text_elem = _svg_text(text_x, text_y, text, size=size)
    else:
        text_elem = ""
    
    return line + arrow + text_elem


def generate() -> Path:
    params = _extract_parameters()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Ajustar dimensiones para mejor visualización
    width = params.base_m + max(params.stirrup_width_m, 0.4) + 0.8
    height = params.height_m + 0.6
    origin_x = 0.2
    origin_y = params.height_m + 0.25

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.2f} {height:.2f}" width="800" height="600">',
        '<g stroke="black" fill="none" font-family="Arial, sans-serif">',
    ]

    # ==================== SECCIÓN PRINCIPAL ====================
    # Rectángulo principal de la viga
    svg_parts.append(_svg_rect(origin_x, origin_y - params.height_m, params.base_m, params.height_m, fill="#f0f0f0"))
    
    # Líneas punteadas del estribo interno
    inner_x = origin_x + params.stirrup_offset_x
    inner_y = origin_y - params.stirrup_offset_y
    svg_parts.append(
        _svg_rect(
            inner_x,
            inner_y - params.stirrup_height_m,
            params.stirrup_width_m,
            params.stirrup_height_m,
            stroke_width=1.5,
            dash="5 3",
            stroke="#0066cc"
        )
    )

    # ==================== BARRAS DE REFUERZO ====================
    # Barras superiores (3 barras)
    num_barras_sup = 3
    espacio_barras_sup = (params.stirrup_width_m - num_barras_sup * BAR_RADIUS_M * 2) / (num_barras_sup + 1)
    
    for i in range(num_barras_sup):
        bx = inner_x + BAR_RADIUS_M + espacio_barras_sup + i * (BAR_RADIUS_M * 2 + espacio_barras_sup)
        by = inner_y - params.stirrup_height_m + BAR_RADIUS_M + espacio_barras_sup
        svg_parts.append(_svg_circle(bx, by, BAR_RADIUS_M))
    
    # Barras inferiores (2 barras)
    num_barras_inf = 2
    espacio_barras_inf = (params.stirrup_width_m - num_barras_inf * BAR_RADIUS_M * 2) / (num_barras_inf + 1)
    
    for i in range(num_barras_inf):
        bx = inner_x + BAR_RADIUS_M + espacio_barras_inf + i * (BAR_RADIUS_M * 2 + espacio_barras_inf)
        by = inner_y - BAR_RADIUS_M - espacio_barras_inf
        svg_parts.append(_svg_circle(bx, by, BAR_RADIUS_M))

    # ==================== DIMENSIONES DE LA SECCIÓN ====================
    # Dimensiones principales
    svg_parts.append(_svg_arrow(origin_x, origin_y + 0.05, origin_x + params.base_m, origin_y + 0.05, f"B = {params.base_m:.2f} m"))
    svg_parts.append(_svg_arrow(origin_x - 0.05, origin_y, origin_x - 0.05, origin_y - params.height_m, f"H = {params.height_m:.2f} m"))
    
    # Dimensiones del recubrimiento
    svg_parts.append(_svg_arrow(origin_x, origin_y - params.height_m + params.stirrup_offset_y/2, 
                               inner_x, origin_y - params.height_m + params.stirrup_offset_y/2, 
                               f"{params.cover_m*100:.0f} cm"))
    svg_parts.append(_svg_arrow(inner_x + params.stirrup_width_m, origin_y - params.height_m + params.stirrup_offset_y/2,
                               origin_x + params.base_m, origin_y - params.height_m + params.stirrup_offset_y/2,
                               f"{params.cover_m*100:.0f} cm"))
    
    # Textos descriptivos
    svg_parts.append(_svg_text(origin_x - 0.08, origin_y - params.height_m + params.stirrup_offset_y + BAR_RADIUS_M, 
                              "Barras Superiores", size=11, anchor="end", rotation=90))
    svg_parts.append(_svg_text(origin_x - 0.08, origin_y - params.stirrup_offset_y - BAR_RADIUS_M,
                              "Barras Inferiores", size=11, anchor="end", rotation=90))

    # ==================== DETALLE DEL ESTRIBO ====================
    # Posición del detalle del estribo (a la derecha de la sección)
    stirrup_detail_x = origin_x + params.base_m + 0.4
    stirrup_detail_y = origin_y - params.height_m/2
    
    # Dibujar estribo con forma más realista (similar a la imagen)
    estribo_width = params.stirrup_width_m * 0.8  # Escalar para mejor visualización
    estribo_height = params.stirrup_height_m * 0.8
    
    # Puntos del estribo (rectángulo con ganchos)
    hook_length = estribo_width * 0.15  # Longitud del gancho
    
    # Rectángulo principal del estribo
    estribo_points = [
        (stirrup_detail_x, stirrup_detail_y - estribo_height/2),  # Esquina superior izquierda
        (stirrup_detail_x + estribo_width, stirrup_detail_y - estribo_height/2),  # Esquina superior derecha
        (stirrup_detail_x + estribo_width, stirrup_detail_y + estribo_height/2),  # Esquina inferior derecha
        (stirrup_detail_x, stirrup_detail_y + estribo_height/2),  # Esquina inferior izquierda
        (stirrup_detail_x, stirrup_detail_y - estribo_height/2),  # Cerrar rectángulo
    ]
    
    # Gancho superior (135°)
    hook_start_x = stirrup_detail_x + estribo_width
    hook_start_y = stirrup_detail_y - estribo_height/2
    
    # Gancho de 135° - más preciso
    hook_points = []
    if params.hook_type == "135":
        # Gancho de 135 grados (más realista)
        hook_points = [
            (hook_start_x, hook_start_y),
            (hook_start_x + hook_length * 0.7, hook_start_y - hook_length * 0.7),  # 45°
            (hook_start_x + hook_length * 0.7 + hook_length * 0.5, hook_start_y - hook_length * 0.7 - hook_length * 0.5),  # 90°
            (hook_start_x + hook_length * 0.7 + hook_length * 0.5 - hook_length * 0.3, 
             hook_start_y - hook_length * 0.7 - hook_length * 0.5 - hook_length * 0.3),  # 135°
        ]
    
    # Unir todos los puntos del estribo
    all_points = estribo_points + hook_points
    
    # Dibujar el estribo
    svg_parts.append(_svg_polyline(all_points, stroke_width=2, stroke="#0066cc"))
    
    # También dibujar un gancho en la esquina inferior izquierda para simetría
    hook2_start_x = stirrup_detail_x
    hook2_start_y = stirrup_detail_y + estribo_height/2
    
    if params.hook_type == "135":
        hook2_points = [
            (hook2_start_x, hook2_start_y),
            (hook2_start_x - hook_length * 0.7, hook2_start_y + hook_length * 0.7),  # 45°
            (hook2_start_x - hook_length * 0.7 - hook_length * 0.5, hook2_start_y + hook_length * 0.7 + hook_length * 0.5),  # 90°
            (hook2_start_x - hook_length * 0.7 - hook_length * 0.5 + hook_length * 0.3, 
             hook2_start_y + hook_length * 0.7 + hook_length * 0.5 + hook_length * 0.3),  # 135°
        ]
        svg_parts.append(_svg_polyline(hook2_points, stroke_width=2, stroke="#0066cc"))

    # Dimensiones del estribo
    svg_parts.append(_svg_arrow(stirrup_detail_x, stirrup_detail_y - estribo_height/2 - 0.05,
                               stirrup_detail_x + estribo_width, stirrup_detail_y - estribo_height/2 - 0.05,
                               f"{params.stirrup_width_m:.2f} m", size=9))
    
    svg_parts.append(_svg_arrow(stirrup_detail_x + estribo_width + 0.05, stirrup_detail_y - estribo_height/2,
                               stirrup_detail_x + estribo_width + 0.05, stirrup_detail_y + estribo_height/2,
                               f"{params.stirrup_height_m:.2f} m", size=9))

    # Texto del estribo
    svg_parts.append(_svg_text(stirrup_detail_x + estribo_width/2, stirrup_detail_y - estribo_height/2 - 0.1,
                              f"Estribo Ø{params.stirrup_diameter}", size=11, weight="bold"))
    svg_parts.append(_svg_text(stirrup_detail_x + estribo_width/2, stirrup_detail_y - estribo_height/2 - 0.15,
                              f"Gancho {params.hook_type}°", size=10))

    # ==================== RESUMEN DE DATOS ====================
    summary_x = stirrup_detail_x + estribo_width + 0.3
    summary_y = stirrup_detail_y - estribo_height/2
    
    # Fondo para el resumen
    summary_width = 0.35
    summary_height = 0.25
    svg_parts.append(_svg_rect(summary_x - 0.05, summary_y - summary_height, summary_width, summary_height, 
                              fill="#e8f4f8", stroke="#b0d0e0", stroke_width=1))
    
    summary_lines = [
        f"B = {params.base_m:.2f} m",
        f"H = {params.height_m:.2f} m",
        f"Recubrimiento = {params.cover_m*100:.0f} cm",
        f"Estribo útil = {params.stirrup_width_m:.2f} m x {params.stirrup_height_m:.2f} m",
        f"Gancho {params.hook_type}° ({params.stirrup_diameter})",
    ]
    
    for idx, line in enumerate(summary_lines):
        svg_parts.append(_svg_text(summary_x, summary_y - 0.05 - idx * 0.04, line, size=9, anchor="start"))

    # ==================== LÍNEAS DE REFERENCIA ====================
    # Línea de referencia entre sección y detalle del estribo
    svg_parts.append(_svg_line(origin_x + params.base_m + 0.1, origin_y - params.height_m/2,
                              stirrup_detail_x - 0.1, stirrup_detail_y,
                              stroke_width=1, stroke="#888"))
    svg_parts.append(_svg_text((origin_x + params.base_m + stirrup_detail_x)/2, origin_y - params.height_m/2 - 0.02,
                              "Detalle", size=9, anchor="middle"))

    svg_parts.append("</g></svg>")

    OUTPUT_FILE.write_text("\n".join(svg_parts), encoding="utf-8")
    return OUTPUT_FILE


def main() -> None:
    output = generate()
    print(f"Esquema guardado en: {output}")


if __name__ == "__main__":
    main()