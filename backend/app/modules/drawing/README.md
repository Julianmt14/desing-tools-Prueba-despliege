# Módulo de Graficación de Despieces

Este paquete agrupa los contratos y utilidades que usarán los nuevos servicios de graficación/exportación.

## Convenciones de unidades

- La geometría estructural permanece en **metros** tal como proviene del motor de despiece.
- Las primitivas de dibujo se expresan en **milímetros** para alinear el documento CAD/SVG final.
- La conversión estándar es `mm = m * 1000`. El factor se declara explícitamente en `DrawingUnits` para evitar duplicar constantes.
- Las dimensiones de sección provenientes del formulario (cm) se convierten internamente a metros para cálculos y a milímetros al renderizar.
- Los recubrimientos, separaciones de estribos y longitudes mínimas de traslape se almacenan en la unidad fuente original, pero siempre se incluye el factor de conversión correspondiente en el payload enviado al render.

## Flujo de datos

1. `design_service.build_beam_drawing_payload` obtiene el diseño, normaliza la geometría y adjunta los resultados de detallado (`DetailingResults`).
2. Los renderizadores consumen `BeamDrawingPayload` y producen un `DrawingDocument` abstracto (colección de líneas, textos, cotas, hatches).
3. Los exportadores (DWG/PDF/SVG) convierten el `DrawingDocument` en archivos descargables.

Toda la configuración específica de normas (NSR-10, ACI) se versionará mediante plantillas descritas en `templates/manifest.json` en etapas posteriores.
