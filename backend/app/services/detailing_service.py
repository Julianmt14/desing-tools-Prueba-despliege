from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import math
import logging
from collections import Counter, defaultdict

from app.schemas.tools.despiece import (
    DetailingResults,
    RebarDetail,
    ProhibitedZone,
    MaterialItem,
    DetailingResponse
)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class DetailingDebugger:
    """Pequeño ayudante para exponer el avance del cálculo en los logs."""

    def __init__(self, name: str = "detailing") -> None:
        self.step = 0
        self.name = name.upper()

    def log(self, message: str, **context: Any) -> None:
        self.step += 1
        context_str = " ".join(
            f"{key}={value}" for key, value in context.items() if value is not None
        )
        if context_str:
            logger.info("%s[%02d] %s | %s", self.name, self.step, message, context_str)
        else:
            logger.info("%s[%02d] %s", self.name, self.step, message)

    def error(self, message: str) -> None:
        logger.error("%s[ERR] %s", self.name, message)

class BeamDetailingService:
    """Servicio para cálculo de despiece automático según NSR-10"""
    
    def __init__(self):
        # Factores NSR-10 según clase de disipación de energía
        self.energy_factors = {
            'DES': 1.3,  # Alta disipación - Empalmes Clase B
            'DMO': 1.0,  # Disipación moderada
            'DMI': 1.0   # Disipación mínima
        }

        self.min_edge_cover_m = 0.05  # 5 cm mínimo en extremos
        self.hook_length_table = {
            '#2': {'90': 0.10, '180': 0.080, '135': 0.075},
            '#3': {'90': 0.15, '180': 0.130, '135': 0.095},
            '#4': {'90': 0.20, '180': 0.150, '135': 0.127},
            '#5': {'90': 0.25, '180': 0.180, '135': 0.159},
            '#6': {'90': 0.30, '180': 0.210, '135': 0.191},
            '#7': {'90': 0.36, '180': 0.250, '135': 0.222},
            '#8': {'90': 0.41, '180': 0.300, '135': 0.254},
            '#9': {'90': 0.49, '180': 0.340, '135': None},
            '#10': {'90': 0.54, '180': 0.400, '135': None},
            '#11': {'90': 0.59, '180': 0.430, '135': None},
            '#14': {'90': 0.80, '180': 0.445, '135': None},
            '#18': {'90': 1.03, '180': 0.572, '135': None},
        }
        
        # Pesos por metro lineal según diámetro (kg/m) - NSR-10 Anexo C
        self.rebar_weights = {
            '#3': 0.56, '#4': 1.00, '#5': 1.55, '#6': 2.26,
            '#7': 3.04, '#8': 3.97, '#9': 5.06, '#10': 6.40,
            '#11': 7.91, '#14': 14.60, '#18': 23.70
        }
        
        # Longitudes de desarrollo base (m) para fy=420MPa, f'c=21MPa
        # NSR-10 C.12.2 - Valores simplificados
        self.base_development_lengths = {
            '#3': 0.30, '#4': 0.40, '#5': 0.50, '#6': 0.60,
            '#7': 0.70, '#8': 0.80, '#9': 0.90, '#10': 1.00,
            '#11': 1.10, '#14': 1.40, '#18': 1.80
        }
        
        # Factores de ajuste para diferentes resistencias de concreto
        self.fc_factors = {
            '21 MPa (3000 psi)': 1.0,
            '24 MPa (3500 psi)': 0.92,
            '28 MPa (4000 psi)': 0.85,
            '32 MPa (4600 psi)': 0.80
        }

        self.fc_column_map = {
            '21 MPa (3000 psi)': 'fc_21_mpa_m',
            '24 MPa (3500 psi)': 'fc_24_mpa_m',
            '28 MPa (4000 psi)': 'fc_28_mpa_m',
            '32 MPa (4600 psi)': 'fc_28_mpa_m',
        }
        
        # Factores para diferentes grados de acero
        self.fy_factors = {
            '420 MPa (Grado 60)': 1.0,
            '520 MPa (Grado 75)': 1.25
        }
    
    def compute_detailing(self, data: Dict[str, Any]) -> DetailingResponse:
        """
        Calcula el despiece automático basado en NSR-10 Título C.
        
        Args:
            data: Diccionario con los datos de la viga
            
        Returns:
            DetailingResponse con los resultados del cálculo
        """
        start_time = datetime.now()
        debugger = DetailingDebugger()
        debugger.log(
            "Inicio de cálculo",
            spans=len(data.get('span_geometries', []) or []),
            supports=len(data.get('axis_supports', []) or []),
        )
        
        try:
            logger.info("Iniciando cálculo de despiece NSR-10")
            
            # 1. Validar y preprocesar datos
            beam_data = self._preprocess_data(data)
            if not beam_data:
                debugger.error("Datos de entrada inválidos")
                return DetailingResponse(
                    success=False,
                    results=None,
                    computation_time_ms=None,
                    message="Datos de entrada inválidos"
                )
            debugger.log(
                "Datos preprocesados",
                top_bars=len(beam_data.get('top_bars', [])),
                bottom_bars=len(beam_data.get('bottom_bars', [])),
            )
            
            # 2. Calcular geometría de la viga
            coordinates = self._calculate_coordinates(beam_data)
            debugger.log(
                "Geometría calculada",
                total_length=f"{coordinates.get('total_length', 0):.2f}m",
                spans=len(coordinates.get('spans', [])),
            )
            
            # 3. Identificar barras continuas obligatorias (NSR-10 C.21.5.2.1)
            continuous_bars = self._identify_continuous_bars(beam_data)
            debugger.log(
                "Barras continuas identificadas",
                top=continuous_bars['top']['total_continuous'],
                bottom=continuous_bars['bottom']['total_continuous'],
            )
            
            # 4. Calcular zonas prohibidas para empalmes (NSR-10 C.21.5.3.2)
            prohibited_zones = self._calculate_prohibited_zones(coordinates, beam_data)
            debugger.log("Zonas prohibidas calculadas", zonas=len(prohibited_zones))
            
            # 5. Calcular longitud de desarrollo ajustada
            development_lengths = self._calculate_development_lengths(beam_data)
            debugger.log("Longitudes de desarrollo evaluadas")
            
            # 6. Generar detalle de barras superiores
            top_bars = self._detail_top_bars(
                beam_data, coordinates, prohibited_zones, 
                continuous_bars, development_lengths
            )
            debugger.log("Detalle barras superiores", barras=len(top_bars))
            
            # 7. Generar detalle de barras inferiores
            bottom_bars = self._detail_bottom_bars(
                beam_data, coordinates, prohibited_zones,
                continuous_bars, development_lengths
            )
            debugger.log("Detalle barras inferiores", barras=len(bottom_bars))

            top_bars, bottom_bars = self._coordinate_splice_positions(
                top_bars,
                bottom_bars,
                prohibited_zones,
                coordinates['total_length'],
            )
            debugger.log("Empalmes coordinados", total_top=len(top_bars), total_bottom=len(bottom_bars))
            
            # 8. Aplicar refuerzo de segmentos específicos
            if beam_data.get('segment_reinforcements'):
                self._apply_segment_reinforcement(
                    beam_data, top_bars, bottom_bars, coordinates
                )
                debugger.log(
                    "Refuerzo segmentado aplicado",
                    segmentos=len(beam_data.get('segment_reinforcements', [])),
                )

            edge_cover = beam_data.get('edge_cover_m', self.min_edge_cover_m)
            max_bar_length = beam_data.get('max_bar_length_m', 12.0)
            self._apply_cover_and_hook_adjustments(
                top_bars,
                coordinates['total_length'],
                edge_cover,
                max_bar_length,
            )
            self._apply_cover_and_hook_adjustments(
                bottom_bars,
                coordinates['total_length'],
                edge_cover,
                max_bar_length,
            )
            
            # 9. Optimizar cortes y generar lista de materiales
            material_list = self._generate_material_list(
                top_bars + bottom_bars, beam_data
            )
            debugger.log(
                "Lista de materiales generada",
                items=len(material_list),
            )
            
            # 10. Validaciones NSR-10
            warnings = self._validate_nsr10(
                beam_data, top_bars, bottom_bars, 
                prohibited_zones, continuous_bars
            )
            debugger.log("Validaciones NSR-10 completadas", advertencias=len(warnings))
            
            # 11. Calcular métricas generales
            total_weight = sum(item.weight_kg for item in material_list)
            total_bars = len(top_bars) + len(bottom_bars)
            
            # 12. Preparar resultados
            results = DetailingResults(
                top_bars=top_bars,
                bottom_bars=bottom_bars,
                prohibited_zones=prohibited_zones,
                material_list=material_list,
                continuous_bars=continuous_bars,
                warnings=warnings,
                validation_passed=len(warnings) == 0,
                total_weight_kg=total_weight,
                total_bars_count=total_bars
            )
            
            computation_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Cálculo completado en {computation_time:.2f}ms")
            debugger.log(
                "Cálculo finalizado",
                tiempo_ms=f"{computation_time:.2f}",
                peso_total=f"{total_weight:.2f}kg",
            )
            
            return DetailingResponse(
                success=True,
                results=results,
                computation_time_ms=computation_time,
                message="Despiece calculado exitosamente según NSR-10"
            )
            
        except Exception as e:
            logger.error(f"Error en cálculo de despiece: {str(e)}", exc_info=True)
            debugger.error(f"Excepción: {str(e)}")
            return DetailingResponse(
                success=False,
                results=None,
                computation_time_ms=None,
                message=f"Error en cálculo: {str(e)}"
            )
    
    def _preprocess_data(self, data: Dict) -> Optional[Dict]:
        """Valida y preprocesa los datos de entrada"""
        try:
            processed = data.copy()
            
            # Validar datos requeridos
            required_fields = ['span_geometries', 'axis_supports', 'top_bars_config', 
                             'bottom_bars_config', 'concrete_strength', 'reinforcement']
            for field in required_fields:
                if field not in processed:
                    logger.error(f"Campo requerido faltante: {field}")
                    return None
            
            # Convertir longitud máxima de barras
            max_length_str = processed.get('max_rebar_length_m', '12m')
            try:
                processed['max_bar_length_m'] = float(max_length_str.replace('m', ''))
            except ValueError:
                processed['max_bar_length_m'] = 12.0
            
            # Expandir configuraciones de barras
            processed['top_bars'] = self._expand_bar_config(processed.get('top_bars_config', []))
            processed['bottom_bars'] = self._expand_bar_config(processed.get('bottom_bars_config', []))
            
            # Validar que haya barras
            if not processed['top_bars'] and not processed['bottom_bars']:
                logger.error("No se definieron barras de refuerzo")
                return None
            
            # Calcular peralte efectivo promedio (simplificado)
            spans = processed.get('span_geometries', [])
            if spans:
                avg_height = sum(span.get('section_height_cm', 0) for span in spans) / len(spans)
                processed['effective_depth_m'] = max(0.3, (avg_height - 6) / 100)  # Restar recubrimiento
            else:
                processed['effective_depth_m'] = 0.45  # Valor por defecto

            cover_cm = processed.get('cover_cm', 5) or 5
            processed['edge_cover_m'] = max(self.min_edge_cover_m, cover_cm / 100)
            
            return processed
            
        except Exception as e:
            logger.error(f"Error en preprocesamiento: {str(e)}")
            return None
    
    def _expand_bar_config(self, config: List[Dict]) -> List[str]:
        """Convierte configuración de barras a lista expandida"""
        bars = []
        for group in config:
            try:
                quantity = int(group.get('quantity', 0))
                diameter = str(group.get('diameter', '')).strip()
                if quantity > 0 and diameter and diameter in self.rebar_weights:
                    bars.extend([diameter] * quantity)
            except (ValueError, TypeError):
                continue
        return bars
    
    def _calculate_coordinates(self, beam_data: Dict) -> Dict:
        """Calcula coordenadas a lo largo de la viga"""
        spans = beam_data.get('span_geometries', [])
        supports = beam_data.get('axis_supports', [])
        
        current_x = 0.0
        coordinates = {
            'faces': [],      # Caras de apoyos
            'centers': [],    # Centros de luces
            'spans': [],      # Intervalos de luces
            'supports': [],   # Intervalos de apoyos
            'total_length': 0
        }
        
        # Procesar cada apoyo y luz
        for i in range(len(supports)):
            support = supports[i] if i < len(supports) else {}
            support_width = support.get('support_width_cm', 0) / 100.0  # a metros
            
            # Guardar cara de apoyo
            face_info = {
                'x': current_x,
                'type': 'support_face',
                'support_index': i,
                'width': support_width,
                'label': support.get('label', f'EJE {i+1}')
            }
            coordinates['faces'].append(face_info)
            
            # Intervalo de apoyo
            if support_width > 0:
                support_interval = {
                    'start': current_x,
                    'end': current_x + support_width,
                    'type': 'support',
                    'index': i
                }
                coordinates['supports'].append(support_interval)
            
            current_x += support_width
            
            # Si hay luz después de este apoyo
            if i < len(spans):
                span = spans[i]
                span_length = span.get('clear_span_between_supports_m', 0)
                
                # Centro de la luz
                center_info = {
                    'x': current_x + span_length / 2,
                    'type': 'span_center',
                    'span_index': i,
                    'length': span_length,
                    'height_cm': span.get('section_height_cm', 0),
                    'base_cm': span.get('section_base_cm', 0)
                }
                coordinates['centers'].append(center_info)
                
                # Intervalo de luz
                span_interval = {
                    'start': current_x,
                    'end': current_x + span_length,
                    'type': 'span',
                    'index': i,
                    'length': span_length
                }
                coordinates['spans'].append(span_interval)
                
                current_x += span_length
        
        coordinates['total_length'] = current_x
        return coordinates
    
    def _identify_continuous_bars(self, beam_data: Dict) -> Dict:
        """Identifica barras continuas obligatorias según NSR-10 C.21.5.2.1"""
        top_bars = beam_data.get('top_bars', [])
        bottom_bars = beam_data.get('bottom_bars', [])
        
        if not top_bars and not bottom_bars:
            return {'top': {'diameters': [], 'count_per_diameter': {}},
                   'bottom': {'diameters': [], 'count_per_diameter': {}}}
        
        # Contar diámetros
        top_counter = Counter(top_bars)
        bottom_counter = Counter(bottom_bars)
        
        # Ordenar diámetros de mayor a menor
        def get_diameter_num(diam: str) -> int:
            try:
                return int(diam.replace('#', ''))
            except ValueError:
                return 0
        
        top_diameters = sorted(top_counter.keys(), key=get_diameter_num, reverse=True)
        bottom_diameters = sorted(bottom_counter.keys(), key=get_diameter_num, reverse=True)
        
        # Seleccionar máximo 2 diámetros más grandes para continuas
        continuous_top_diameters = top_diameters[:2]
        continuous_bottom_diameters = bottom_diameters[:2]
        
        # Determinar cuántas de cada diámetro deben ser continuas (mínimo 1, máximo 2)
        top_count_per_diameter = {}
        for diam in continuous_top_diameters:
            available = top_counter[diam]
            top_count_per_diameter[diam] = min(2, available) if available >= 2 else min(1, available)
        
        bottom_count_per_diameter = {}
        for diam in continuous_bottom_diameters:
            available = bottom_counter[diam]
            bottom_count_per_diameter[diam] = min(2, available) if available >= 2 else min(1, available)
        
        return {
            'top': {
                'diameters': continuous_top_diameters,
                'count_per_diameter': top_count_per_diameter,
                'total_continuous': sum(top_count_per_diameter.values())
            },
            'bottom': {
                'diameters': continuous_bottom_diameters,
                'count_per_diameter': bottom_count_per_diameter,
                'total_continuous': sum(bottom_count_per_diameter.values())
            }
        }
    
    def _calculate_prohibited_zones(self, coordinates: Dict, beam_data: Dict) -> List[ProhibitedZone]:
        """Calcula zonas donde no se permiten empalmes según NSR-10 C.21.5.3.2"""
        zones: List[ProhibitedZone] = []
        d = beam_data.get('effective_depth_m', 0.5)
        faces = coordinates.get('faces', [])
        spans = coordinates.get('spans', [])
        total_supports = len(faces)

        for face in faces:
            if face.get('type') != 'support_face':
                continue

            support_index = face.get('support_index', 0)
            support_width = face.get('width', 0.0)
            support_start = face.get('x', 0.0)
            support_end = support_start + support_width
            support_half_width = support_width / 2
            prohibited_distance = max(2 * d, support_half_width)
            label = face.get('label') or f"Eje {support_index + 1}"
            is_first = support_index == 0
            is_last = support_index == total_supports - 1

            # Zona correspondiente al propio apoyo
            if support_end - support_start > 0:
                zones.append(
                    ProhibitedZone(
                        start_m=support_start,
                        end_m=support_end,
                        type='no_splice_zone',
                        description=f"No empalmar dentro del apoyo {label} (ancho {support_width*100:.0f} cm)",
                        support_index=support_index,
                    )
                )

            # Zona posterior (solo si no es el apoyo final)
            if not is_last:
                right_limit = coordinates.get('total_length', support_end)
                for span in spans:
                    if abs(span.get('start', -999) - support_end) < 0.01:
                        right_limit = min(right_limit, span['start'] + span.get('length', 0) / 2)
                        break

                zone_start = support_end
                zone_end = min(support_end + prohibited_distance, right_limit)
                if zone_end > zone_start:
                    zones.append(
                        ProhibitedZone(
                            start_m=zone_start,
                            end_m=zone_end,
                            type='no_splice_zone',
                            description=f"No empalmar: {prohibited_distance*100:.0f} cm después de {label}",
                            support_index=support_index,
                        )
                    )

            # Zona anterior (solo si no es el primer apoyo)
            if not is_first:
                left_limit = 0.0
                for span in spans:
                    if abs(span.get('end', -999) - support_start) < 0.01:
                        left_limit = max(left_limit, span['end'] - span.get('length', 0) / 2)
                        break

                zone_start = max(support_start - prohibited_distance, left_limit)
                zone_end = support_start
                if zone_start < zone_end:
                    zones.append(
                        ProhibitedZone(
                            start_m=zone_start,
                            end_m=zone_end,
                            type='no_splice_zone',
                            description=f"No empalmar: {prohibited_distance*100:.0f} cm antes de {label}",
                            support_index=support_index,
                        )
                    )

        zones.sort(key=lambda z: z.start_m)
        return zones
    
    def _calculate_development_lengths(self, beam_data: Dict) -> Dict[str, float]:
        """Calcula longitudes de desarrollo ajustadas según NSR-10 C.12.2"""
        development_lengths = {}
        concrete_strength = beam_data.get('concrete_strength', '21 MPa (3000 psi)')
        reinforcement = beam_data.get('reinforcement', '420 MPa (Grado 60)')
        
        fc_factor = self.fc_factors.get(concrete_strength, 1.0)
        fy_factor = self.fy_factors.get(reinforcement, 1.0)
        energy_factor = self.energy_factors.get(beam_data.get('energy_dissipation_class', 'DES'), 1.0)
        lap_lookup = beam_data.get('lap_splice_lookup') or {}
        fc_column = self.fc_column_map.get(concrete_strength)
        
        for diameter, base_length in self.base_development_lengths.items():
            # Longitud básica ajustada por f'c y fy
            adjusted_length = base_length * fc_factor * fy_factor
            
            # Para empalmes clase B en zonas sísmicas
            splice_length = adjusted_length * energy_factor
            if fc_column and diameter in lap_lookup:
                lap_value = lap_lookup[diameter].get(fc_column)
                if lap_value:
                    splice_length = float(lap_value)
            
            development_lengths[diameter] = {
                'development': adjusted_length,
                'splice': splice_length
            }
        
        return development_lengths
    
    def _detail_top_bars(self, beam_data: Dict, coordinates: Dict, 
                        prohibited_zones: List[ProhibitedZone],
                        continuous_bars: Dict, development_lengths: Dict) -> List[RebarDetail]:
        """Genera detalle para barras superiores"""
        bars = []
        top_bars = beam_data.get('top_bars', [])
        max_length = beam_data.get('max_bar_length_m', 12.0)
        hook_type = beam_data.get('hook_type', '135')
        edge_cover = beam_data.get('edge_cover_m', self.min_edge_cover_m)
        
        if not top_bars:
            return bars
        
        # Agrupar por diámetro
        bar_counter = Counter(top_bars)
        
        for diameter, total_count in bar_counter.items():
            dev_info = development_lengths.get(diameter, {'development': 0.6, 'splice': 0.78})
            
            # Determinar cuántas son continuas
            continuous_count = continuous_bars['top']['count_per_diameter'].get(diameter, 0)
            
            # Barras continuas
            for i in range(continuous_count):
                bar_id = f"T{diameter.replace('#', '')}-C{i+1:02d}"
                splices = self._calculate_splices(
                    total_length=coordinates['total_length'],
                    max_bar_length=max_length,
                    prohibited_zones=prohibited_zones,
                    splice_length=dev_info['splice']
                )
                
                bar = RebarDetail(
                    id=bar_id,
                    diameter=diameter,
                    position='top',
                    type='continuous',
                    length_m=coordinates['total_length'],
                    start_m=0.0,
                    end_m=coordinates['total_length'],
                    splices=splices,
                    hook_type=hook_type,
                    quantity=1,
                    development_length_m=dev_info['development'],
                    notes="Barra continua - NSR-10 C.21.5.2.1"
                )
                segments = self._split_bar_by_max_length(
                    bar,
                    max_length=max_length,
                    splice_length=dev_info['splice'],
                    prohibited_zones=prohibited_zones,
                    hook_length=self._get_single_hook_length(diameter, hook_type),
                    edge_cover=edge_cover,
                    beam_length=coordinates['total_length'],
                    is_bottom_bar=False,
                )
                bars.extend(segments)
            
            # Barras restantes (de apoyo)
            remaining_count = total_count - continuous_count
            if remaining_count > 0:
                # Distribuir en apoyos
                support_bars = self._distribute_support_bars(
                    diameter=diameter,
                    count=remaining_count,
                    coordinates=coordinates,
                    position='top',
                    hook_type=hook_type,
                    development_length=dev_info['development']
                )
                bars.extend(support_bars)
        
        return bars
    
    def _detail_bottom_bars(self, beam_data: Dict, coordinates: Dict,
                           prohibited_zones: List[ProhibitedZone],
                           continuous_bars: Dict, development_lengths: Dict) -> List[RebarDetail]:
        """Genera detalle para barras inferiores"""
        bars = []
        bottom_bars = beam_data.get('bottom_bars', [])
        max_length = beam_data.get('max_bar_length_m', 12.0)
        hook_type = beam_data.get('hook_type', '135')
        edge_cover = beam_data.get('edge_cover_m', self.min_edge_cover_m)
        
        if not bottom_bars:
            return bars
        
        # Agrupar por diámetro
        bar_counter = Counter(bottom_bars)
        
        for diameter, total_count in bar_counter.items():
            dev_info = development_lengths.get(diameter, {'development': 0.6, 'splice': 0.78})
            
            # Determinar cuántas son continuas
            continuous_count = continuous_bars['bottom']['count_per_diameter'].get(diameter, 0)
            
            # Barras continuas
            for i in range(continuous_count):
                bar_id = f"B{diameter.replace('#', '')}-C{i+1:02d}"
                total_length = coordinates['total_length']
                splices = self._build_bottom_splice_plan(
                    total_length=total_length,
                    splice_length=dev_info['splice'],
                    prohibited_zones=prohibited_zones,
                    max_bar_length=max_length,
                    bar_index=i,
                )
                offset_ratio_groups = [0.08, 0.16, 0.24]
                splice_offset_ratio = offset_ratio_groups[i % len(offset_ratio_groups)]
                
                bar = RebarDetail(
                    id=bar_id,
                    diameter=diameter,
                    position='bottom',
                    type='continuous',
                    length_m=total_length,
                    start_m=0.0,
                    end_m=total_length,
                    splices=splices,
                    hook_type=hook_type,
                    quantity=1,
                    development_length_m=dev_info['development'],
                    notes="Barra continua - NSR-10 C.21.5.2.1"
                )
                segments = self._split_bar_by_max_length(
                    bar,
                    max_length=max_length,
                    splice_length=dev_info['splice'],
                    prohibited_zones=prohibited_zones,
                    hook_length=self._get_single_hook_length(diameter, hook_type),
                    edge_cover=edge_cover,
                    beam_length=coordinates['total_length'],
                    prefer_previous_zone=True,
                    splice_offset_ratio=splice_offset_ratio,
                    is_bottom_bar=True,
                )
                bars.extend(segments)
            
            # Barras restantes
            remaining_count = total_count - continuous_count
            if remaining_count > 0:
                # NSR-10: Al menos 1/3 del refuerzo positivo debe entrar al apoyo
                min_into_support = max(1, math.ceil(total_count / 3))
                support_count = max(0, min_into_support - continuous_count)
                
                if support_count > 0:
                    # Barras que entran al apoyo
                    support_bars = self._distribute_span_bars(
                        diameter=diameter,
                        count=support_count,
                        coordinates=coordinates,
                        position='bottom',
                        hook_type=hook_type,
                        development_length=dev_info['development'],
                        bar_type='support_anchored'
                    )
                    bars.extend(support_bars)
                
                # Barras restantes en centro de luz
                span_count = remaining_count - support_count
                if span_count > 0:
                    span_bars = self._distribute_span_bars(
                        diameter=diameter,
                        count=span_count,
                        coordinates=coordinates,
                        position='bottom',
                        hook_type=hook_type,
                        development_length=dev_info['development'],
                        bar_type='span'
                    )
                    bars.extend(span_bars)
        
        return bars
    
    def _calculate_splices(self, total_length: float, max_bar_length: float,
                          prohibited_zones: List[ProhibitedZone], splice_length: float) -> Optional[List[Dict]]:
        """Calcula ubicaciones de empalmes evitando zonas prohibidas"""
        if total_length <= max_bar_length:
            return None
        
        # Determinar número de empalmes necesarios
        num_pieces = math.ceil(total_length / max_bar_length)
        if num_pieces <= 1:
            return None
        
        piece_length = total_length / num_pieces
        splices = []
        
        # Buscar ubicaciones seguras para empalmes
        for i in range(1, num_pieces):
            splice_center = i * piece_length
            
            # Verificar que no esté en zona prohibida
            in_prohibited = False
            for zone in prohibited_zones:
                if zone.start_m <= splice_center <= zone.end_m:
                    in_prohibited = True
                    break
            
            if not in_prohibited:
                splice_start = splice_center - splice_length / 2
                splice_end = splice_center + splice_length / 2
                
                # Asegurar que el empalme no salga de la viga
                splice_start = max(0, splice_start)
                splice_end = min(total_length, splice_end)
                
                if splice_end - splice_start >= splice_length * 0.8:  # Al menos 80% de la longitud requerida
                    splices.append({
                        'start': splice_start,
                        'end': splice_end,
                        'length': splice_end - splice_start,
                        'type': 'lap_splice_class_b'
                    })
        
        return splices if splices else None

    def _build_bottom_splice_plan(
        self,
        *,
        total_length: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
        max_bar_length: float,
        bar_index: int,
    ) -> Optional[List[Dict[str, Any]]]:
        """Genera una lista de empalmes desplazados para barras inferiores continuas."""
        if splice_length <= 0:
            return None

        possible_positions = [0.25, 0.33, 0.40, 0.50, 0.60, 0.67, 0.75]
        pattern_map = {
            0: [1, 5],  # 33% y 67%
            1: [2, 4],  # 40% y 60%
            2: [0, 3],  # 25% y 50%
        }
        group = bar_index % len(pattern_map)
        indices = pattern_map[group]
        splices: List[Dict[str, Any]] = []

        for idx in indices:
            if idx >= len(possible_positions):
                continue
            center_ratio = possible_positions[idx]
            center = total_length * center_ratio
            if self._is_in_prohibited_zone(center, prohibited_zones, splice_length):
                continue
            splice_start = max(0.0, center - splice_length / 2)
            splice_end = min(total_length, center + splice_length / 2)
            if splice_end - splice_start >= splice_length * 0.8:
                splices.append(
                    {
                        "start": splice_start,
                        "end": splice_end,
                        "length": splice_end - splice_start,
                        "type": "lap_splice_class_b",
                        "offset_group": group,
                    }
                )

        if splices:
            return splices

        offset_factor = 0.08 + 0.04 * group
        fallback = self._calculate_splices_with_offset(
            total_length=total_length,
            max_bar_length=max_bar_length,
            prohibited_zones=prohibited_zones,
            splice_length=splice_length,
            offset_factor=offset_factor,
        )
        return fallback

    def _calculate_splices_with_offset(
        self,
        *,
        total_length: float,
        max_bar_length: float,
        prohibited_zones: List[ProhibitedZone],
        splice_length: float,
        offset_factor: float = 0.0,
    ) -> Optional[List[Dict[str, Any]]]:
        """Calcula empalmes aplicando un desplazamiento progresivo para evitar coincidencias."""
        if total_length <= max_bar_length or splice_length <= 0:
            return None

        num_pieces = math.ceil(total_length / max_bar_length)
        if num_pieces <= 1:
            return None

        base_piece_length = total_length / num_pieces
        bounded_offset_factor = max(-0.5, min(offset_factor, 0.5))
        offset_per_joint = base_piece_length * bounded_offset_factor

        splices: List[Dict[str, Any]] = []
        for i in range(1, num_pieces):
            splice_center = i * base_piece_length + offset_per_joint * i
            splice_center = max(splice_length / 2, min(splice_center, total_length - splice_length / 2))

            if self._is_in_prohibited_zone(splice_center, prohibited_zones, splice_length):
                continue

            splice_start = max(0.0, splice_center - splice_length / 2)
            splice_end = min(total_length, splice_center + splice_length / 2)
            if splice_end - splice_start >= splice_length * 0.8:
                splices.append(
                    {
                        "start": splice_start,
                        "end": splice_end,
                        "length": splice_end - splice_start,
                        "type": "lap_splice_class_b",
                        "offset_applied": round(bounded_offset_factor, 3),
                    }
                )

        return splices if splices else None

    @staticmethod
    def _is_in_prohibited_zone(
        position: float,
        prohibited_zones: List[ProhibitedZone],
        splice_length: float,
    ) -> bool:
        splice_start = position - splice_length / 2
        splice_end = position + splice_length / 2
        for zone in prohibited_zones:
            if zone.start_m <= position <= zone.end_m:
                return True
            if splice_start < zone.end_m and splice_end > zone.start_m:
                return True
        return False

    def _split_bar_by_max_length(
        self,
        bar: RebarDetail,
        *,
        max_length: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
        hook_length: float,
        edge_cover: float,
        beam_length: float,
        prefer_previous_zone: bool = False,
        splice_offset_ratio: float = 0.0,
        is_bottom_bar: bool = False,
    ) -> List[RebarDetail]:
        """Segmenta una barra en piezas que respetan la longitud comercial máxima."""
        if max_length <= 0 or bar.length_m <= max_length:
            return [bar]

        if splice_length <= 0 or splice_length >= max_length:
            logger.warning(
                "No se puede segmentar la barra %s porque splice %.2f >= Lmax %.2f",
                bar.id,
                splice_length,
                max_length,
            )
            return [bar]

        if is_bottom_bar:
            return self._split_bottom_bar_strategy(
                bar=bar,
                max_length=max_length,
                splice_length=splice_length,
                prohibited_zones=prohibited_zones,
                hook_length=hook_length,
                edge_cover=edge_cover,
                beam_length=beam_length,
                splice_offset_ratio=splice_offset_ratio,
            )

        return self._split_top_bar_strategy(
            bar=bar,
            max_length=max_length,
            splice_length=splice_length,
            prohibited_zones=prohibited_zones,
            hook_length=hook_length,
            edge_cover=edge_cover,
            beam_length=beam_length,
            prefer_previous_zone=prefer_previous_zone,
        )

    def _split_top_bar_strategy(
        self,
        *,
        bar: RebarDetail,
        max_length: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
        hook_length: float,
        edge_cover: float,
        beam_length: float,
        prefer_previous_zone: bool = False,
    ) -> List[RebarDetail]:
        cover = max(self.min_edge_cover_m, edge_cover or 0.0)
        tolerance = 1e-3
        has_start_hook = bool(hook_length and bar.start_m <= cover + tolerance)
        has_end_hook = bool(
            hook_length and bar.end_m >= beam_length - cover - tolerance
        )

        segments: List[RebarDetail] = []
        joints: List[Dict[str, Any]] = []
        current_start = bar.start_m
        piece_index = 1
        safety_counter = 0

        while current_start < bar.end_m - 1e-6 and safety_counter < 100:
            safety_counter += 1
            remaining_length = max(bar.end_m - current_start, 0.0)
            if remaining_length <= 0:
                break

            hook_deduction = 0.0
            if has_start_hook and piece_index == 1:
                hook_deduction += hook_length
            if has_end_hook and remaining_length <= max_length + tolerance:
                hook_deduction += hook_length

            usable_max = max_length - hook_deduction
            if usable_max <= 0:
                logger.warning(
                    "La barra %s no puede segmentarse porque los ganchos consumen la longitud máxima",
                    bar.id,
                )
                usable_max = max_length

            segment_length = min(usable_max, remaining_length)
            if piece_index == 1 and remaining_length > max_length * 1.8:
                segment_length = min(usable_max * 0.6, remaining_length)

            candidate_end = current_start + segment_length
            is_last_segment = candidate_end >= bar.end_m - tolerance

            if (
                prefer_previous_zone
                and not is_last_segment
                and splice_length > 0
            ):
                joint_start_candidate = max(bar.start_m, candidate_end - splice_length)
                remaining_after_joint = bar.end_m - joint_start_candidate
                if remaining_after_joint <= max_length + tolerance:
                    preferred_end = self._prefer_splice_in_previous_corridor(
                        current_start=current_start,
                        joint_start=joint_start_candidate,
                        candidate_end=candidate_end,
                        splice_length=splice_length,
                        prohibited_zones=prohibited_zones,
                    )
                    if preferred_end < candidate_end - tolerance:
                        candidate_end = preferred_end
                        segment_length = candidate_end - current_start
                        is_last_segment = candidate_end >= bar.end_m - tolerance

            if is_last_segment:
                segment_end = bar.end_m
            else:
                segment_end = self._adjust_segment_end_for_splice_zones(
                    current_start,
                    candidate_end,
                    splice_length,
                    prohibited_zones,
                )

            length = segment_end - current_start
            if length <= 0:
                break

            segment = RebarDetail(
                id=f"{bar.id}-S{piece_index:02d}",
                diameter=bar.diameter,
                position=bar.position,
                type=bar.type,
                length_m=length,
                start_m=current_start,
                end_m=segment_end,
                hook_type=bar.hook_type,
                splices=None,
                quantity=bar.quantity,
                development_length_m=bar.development_length_m,
                notes=f"Segmento {piece_index} - Superior",
            )
            segments.append(segment)

            if segment_end >= bar.end_m - 1e-6:
                break

            joint_start = max(bar.start_m, segment_end - splice_length)
            joint_end = segment_end

            if self._overlaps_prohibited_zone(joint_start, joint_end, prohibited_zones):
                logger.warning(
                    "No se pudo ubicar el empalme de la barra %s fuera de zonas prohibidas",
                    bar.id,
                )

            joints.append(
                {
                    "start": joint_start,
                    "end": joint_end,
                    "length": joint_end - joint_start,
                    "type": "lap_splice_class_b",
                    "position": "top",
                }
            )

            current_start = joint_start
            piece_index += 1

        if safety_counter >= 100:
            logger.warning("Se alcanzó el límite de segmentación para la barra %s", bar.id)

        if not segments:
            return [bar]

        for idx, segment in enumerate(segments):
            segment_splices: List[Dict[str, Any]] = []
            if idx > 0:
                segment_splices.append(joints[idx - 1])
            if idx < len(joints):
                segment_splices.append(joints[idx])
            segment.splices = segment_splices or None

        return segments

    def _split_bottom_bar_strategy(
        self,
        *,
        bar: RebarDetail,
        max_length: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
        hook_length: float,
        edge_cover: float,
        beam_length: float,
        splice_offset_ratio: float = 0.0,
    ) -> List[RebarDetail]:
        logger.info(
            "Dividiendo barra inferior %s con longitud total %.2fm",
            bar.id,
            bar.length_m,
        )
        logger.info("Offset ratio inferior aplicado: %.3f", splice_offset_ratio or 0.0)

        cover = max(self.min_edge_cover_m, edge_cover or 0.0)
        tolerance = 1e-3
        has_start_hook = bool(hook_length and bar.start_m <= cover + tolerance)
        has_end_hook = bool(hook_length and bar.end_m >= beam_length - cover - tolerance)

        total_length = max(bar.end_m - bar.start_m, 0.0)
        offset_ratio = max(0.0, min(splice_offset_ratio or 0.0, 0.6))
        if offset_ratio > tolerance:
            first_segment_target = min(total_length * (0.4 + offset_ratio * 0.5), max_length)
        else:
            first_segment_target = min(total_length * 0.45, max_length * 0.8)
        first_segment_target = max(first_segment_target, splice_length * 1.5)
        first_segment_target = min(first_segment_target, total_length)

        segments: List[RebarDetail] = []
        joints: List[Dict[str, Any]] = []
        current_start = bar.start_m
        piece_index = 1
        safety_counter = 0
        logged_first_segment = False

        while current_start < bar.end_m - 1e-6 and safety_counter < 100:
            safety_counter += 1
            remaining_length = max(bar.end_m - current_start, 0.0)
            if remaining_length <= 0:
                break

            hook_deduction = 0.0
            if has_start_hook and piece_index == 1:
                hook_deduction += hook_length
            if has_end_hook and remaining_length <= max_length + tolerance:
                hook_deduction += hook_length

            usable_max = max_length - hook_deduction
            if usable_max <= 0:
                logger.warning(
                    "La barra %s no puede segmentarse porque los ganchos consumen la longitud máxima",
                    bar.id,
                )
                usable_max = max_length

            segment_length = min(usable_max, remaining_length)
            if piece_index == 1:
                segment_length = min(segment_length, first_segment_target)

            candidate_end = current_start + segment_length
            candidate_end = min(candidate_end, bar.end_m)
            is_last_segment = candidate_end >= bar.end_m - tolerance

            needs_zone_adjustment = True
            corridor_target = None
            if piece_index == 1 and not is_last_segment:
                corridor_target = self._target_bottom_corridor_end(
                    current_start=current_start,
                    candidate_end=candidate_end,
                    splice_length=splice_length,
                    prohibited_zones=prohibited_zones,
                )
                if corridor_target is not None:
                    candidate_end = min(bar.end_m, corridor_target)
                    is_last_segment = candidate_end >= bar.end_m - tolerance
                    needs_zone_adjustment = False
                    logger.info(
                        "Barra %s: empalme dirigido al corredor previo en %.2fm",
                        bar.id,
                        candidate_end,
                    )

            if piece_index == 1 and not is_last_segment and needs_zone_adjustment:
                joint_start_candidate = max(bar.start_m, candidate_end - splice_length)
                joint_end_candidate = candidate_end
                if self._overlaps_prohibited_zone(
                    joint_start_candidate, joint_end_candidate, prohibited_zones
                ):
                    safe_center = self._find_safe_splice_position(
                        start_range=current_start + splice_length,
                        end_range=candidate_end,
                        splice_length=splice_length,
                        prohibited_zones=prohibited_zones,
                    )
                    if safe_center is not None:
                        candidate_end = min(bar.end_m, safe_center)
                        joint_end_candidate = candidate_end
                        joint_start_candidate = joint_end_candidate - splice_length
                        needs_zone_adjustment = False
                        logger.info(
                            "Barra %s: empalme inicial reubicado en %.2fm",
                            bar.id,
                            joint_end_candidate,
                        )
                    else:
                        logger.warning(
                            "Barra %s: no se encontró corredor seguro para el primer empalme",
                            bar.id,
                        )
                else:
                    needs_zone_adjustment = False

            if not is_last_segment and needs_zone_adjustment:
                candidate_end = self._adjust_segment_end_for_splice_zones(
                    current_start,
                    candidate_end,
                    splice_length,
                    prohibited_zones,
                )
                if candidate_end >= bar.end_m - tolerance:
                    is_last_segment = True

            segment_end = bar.end_m if is_last_segment else candidate_end
            length = segment_end - current_start
            if length <= 0:
                break

            segment = RebarDetail(
                id=f"{bar.id}-S{piece_index:02d}",
                diameter=bar.diameter,
                position=bar.position,
                type=bar.type,
                length_m=length,
                start_m=current_start,
                end_m=segment_end,
                hook_type=bar.hook_type,
                splices=None,
                quantity=bar.quantity,
                development_length_m=bar.development_length_m,
                notes=f"Segmento {piece_index} - Inferior",
            )
            segments.append(segment)

            if not logged_first_segment and piece_index == 1:
                logger.info(
                    "Barra inferior %s: primer segmento=%.2fm",
                    bar.id,
                    length,
                )
                logged_first_segment = True

            if segment_end >= bar.end_m - 1e-6:
                break

            joint_start = max(bar.start_m, segment_end - splice_length)
            joint_end = segment_end

            if self._overlaps_prohibited_zone(joint_start, joint_end, prohibited_zones):
                logger.warning(
                    "Barra %s: empalme inferior aún cae en zona prohibida",
                    bar.id,
                )

            joints.append(
                {
                    "start": joint_start,
                    "end": joint_end,
                    "length": joint_end - joint_start,
                    "type": "lap_splice_class_b",
                    "position": "bottom",
                }
            )
            logger.info("Barra inferior %s: empalme en %.2fm", bar.id, joint_end)

            current_start = joint_start
            piece_index += 1

        if safety_counter >= 100:
            logger.warning("Se alcanzó el límite de segmentación para la barra %s", bar.id)

        if not segments:
            return [bar]

        for idx, segment in enumerate(segments):
            segment_splices: List[Dict[str, Any]] = []
            if idx > 0:
                segment_splices.append(joints[idx - 1])
            if idx < len(joints):
                segment_splices.append(joints[idx])
            segment.splices = segment_splices or None

        return segments

    def _prefer_splice_in_previous_corridor(
        self,
        *,
        current_start: float,
        joint_start: float,
        candidate_end: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
    ) -> float:
        """Mueve el empalme final al inicio del corredor antes del apoyo superior."""
        tolerance = 1e-3
        if splice_length <= 0:
            return candidate_end

        before_zone = self._find_next_before_zone(joint_start, prohibited_zones)
        if not before_zone:
            return candidate_end

        prev_end = self._find_zone_end_before(before_zone.start_m, prohibited_zones)
        if prev_end is None or prev_end < current_start + tolerance:
            return candidate_end

        corridor_end = before_zone.start_m - tolerance
        available = corridor_end - prev_end
        if available < splice_length - tolerance:
            return candidate_end

        target_end = prev_end + splice_length
        target_end = min(target_end, corridor_end)
        if target_end <= current_start + tolerance:
            return candidate_end

        return target_end

    @staticmethod
    def _find_overlapping_zone(
        start: float, end: float, zones: List[ProhibitedZone]
    ) -> Optional[ProhibitedZone]:
        for zone in zones:
            if max(start, zone.start_m) < min(end, zone.end_m):
                return zone
        return None

    def _adjust_segment_end_for_splice_zones(
        self,
        current_start: float,
        candidate_end: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
    ) -> float:
        tolerance = 1e-3
        adjusted_end = candidate_end
        attempts = 0

        while attempts < 20:
            attempts += 1
            joint_start = adjusted_end - splice_length
            if joint_start < current_start + tolerance:
                joint_start = current_start + tolerance
            if not self._overlaps_prohibited_zone(joint_start, adjusted_end, prohibited_zones):
                return adjusted_end

            zone = self._find_overlapping_zone(joint_start, adjusted_end, prohibited_zones)
            if not zone:
                break

            shifted_end = zone.start_m - tolerance
            if shifted_end - splice_length <= current_start + tolerance:
                # No hay espacio suficiente antes de la zona; salir y dejar advertencia
                return candidate_end

            adjusted_end = shifted_end

        return adjusted_end

    @staticmethod
    def _find_next_zone_start(position: float, zones: List[ProhibitedZone]) -> Optional[float]:
        tolerance = 1e-3
        for zone in zones:
            if zone.start_m >= position + tolerance:
                return zone.start_m
        return None

    @staticmethod
    def _find_zone_end_before(position: float, zones: List[ProhibitedZone]) -> Optional[float]:
        tolerance = 1e-3
        previous_end = None
        for zone in zones:
            if zone.end_m < position - tolerance:
                previous_end = zone.end_m
            else:
                break
        return previous_end

    @staticmethod
    def _find_next_before_zone(position: float, zones: List[ProhibitedZone]) -> Optional[ProhibitedZone]:
        tolerance = 1e-3
        for zone in zones:
            if zone.start_m >= position + tolerance:
                description = (zone.description or "").lower()
                if "antes" in description:
                    return zone
        return None

    def _coordinate_splice_positions(
        self,
        top_bars: List[RebarDetail],
        bottom_bars: List[RebarDetail],
        prohibited_zones: List[ProhibitedZone],
        beam_length: float,
    ) -> Tuple[List[RebarDetail], List[RebarDetail]]:
        """Ajusta empalmes inferiores para que no coincidan con los superiores."""
        if not bottom_bars or beam_length <= 0:
            return top_bars, bottom_bars

        existing_splices: List[Dict[str, Any]] = []
        for bar in top_bars:
            if not bar.splices:
                continue
            for splice in bar.splices:
                length = splice.get("length") or max(splice.get("end", 0.0) - splice.get("start", 0.0), 0.0)
                center = (splice.get("start", 0.0) + splice.get("end", 0.0)) / 2
                existing_splices.append({"center": center, "length": length, "type": "top"})

        for bar in bottom_bars:
            if not bar.splices:
                continue
            bar_adjusted = False
            for splice in bar.splices:
                length = splice.get("length") or max(splice.get("end", 0.0) - splice.get("start", 0.0), 0.0)
                if length <= 0:
                    continue
                original_center = (splice.get("start", 0.0) + splice.get("end", 0.0)) / 2
                has_conflict = False
                for existing in existing_splices:
                    min_distance = max(length, existing["length"]) * 1.5
                    if abs(original_center - existing["center"]) < min_distance:
                        has_conflict = True
                        break

                if not has_conflict:
                    existing_splices.append({"center": original_center, "length": length, "type": "bottom"})
                    continue

                new_center = self._find_non_conflicting_splice_position(
                    original_center=original_center,
                    splice_length=length,
                    existing_splice_positions=existing_splices,
                    prohibited_zones=prohibited_zones,
                    beam_length=beam_length,
                    bar_id=bar.id,
                )

                if new_center is not None:
                    new_start = max(0.0, new_center - length / 2)
                    new_end = min(beam_length, new_center + length / 2)
                    splice["start"] = new_start
                    splice["end"] = new_end
                    splice["length"] = new_end - new_start
                    splice["adjusted"] = True
                    splice["original_center"] = original_center
                    bar_adjusted = True
                    final_center = (new_start + new_end) / 2
                    existing_splices.append({"center": final_center, "length": splice["length"], "type": "bottom"})
                else:
                    existing_splices.append({"center": original_center, "length": length, "type": "bottom"})
                    logger.warning(
                        "Barra %s: no se pudo evitar coincidencia de empalme en %.2fm",
                        bar.id,
                        original_center,
                    )

            if bar_adjusted:
                note = (bar.notes or "").strip()
                marker = "Empalmes coordinados"
                if marker not in note:
                    bar.notes = f"{note} | {marker}" if note else marker

        return top_bars, bottom_bars

    def _find_non_conflicting_splice_position(
        self,
        *,
        original_center: float,
        splice_length: float,
        existing_splice_positions: List[Dict[str, Any]],
        prohibited_zones: List[ProhibitedZone],
        beam_length: float,
        bar_id: str,
        max_attempts: int = 10,
    ) -> Optional[float]:
        """Busca una nueva posición para el empalme que mantenga separación."""
        if splice_length <= 0:
            return None

        offset_candidates = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        attempts = 0
        while attempts < max_attempts:
            for magnitude in offset_candidates:
                for direction in (1, -1):
                    test_center = original_center + direction * magnitude * (attempts + 1)
                    if test_center < splice_length / 2 or test_center > beam_length - splice_length / 2:
                        continue
                    if self._is_in_prohibited_zone(test_center, prohibited_zones, splice_length):
                        continue
                    conflict = False
                    for existing in existing_splice_positions:
                        min_distance = max(splice_length, existing["length"]) * 1.2
                        if abs(test_center - existing["center"]) < min_distance:
                            conflict = True
                            break
                    if not conflict:
                        return test_center
            attempts += 1

        logger.debug("Barra %s: no se encontró posición alternativa para el empalme", bar_id)
        return None

    def _find_safe_splice_position(
        self,
        *,
        start_range: float,
        end_range: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
        step: float = 0.1,
    ) -> Optional[float]:
        """Busca una posición segura para ubicar el empalme dentro de un rango."""
        tolerance = 1e-3
        if splice_length <= 0 or end_range - start_range <= tolerance:
            return None

        test_positions: List[float] = []
        pos = start_range
        while pos <= end_range + tolerance:
            test_positions.append(pos)
            pos += max(step, tolerance)

        for i in range(len(test_positions) - 1):
            mid = (test_positions[i] + test_positions[i + 1]) / 2
            test_positions.append(mid)

        for position in sorted(set(test_positions)):
            splice_start = position - splice_length / 2
            splice_end = position + splice_length / 2
            overlaps = False
            for zone in prohibited_zones:
                if max(splice_start, zone.start_m) < min(splice_end, zone.end_m):
                    overlaps = True
                    break
            if not overlaps:
                return position

        return None

    def _target_bottom_corridor_end(
        self,
        *,
        current_start: float,
        candidate_end: float,
        splice_length: float,
        prohibited_zones: List[ProhibitedZone],
    ) -> Optional[float]:
        """Ubica el empalme dentro del corredor previo a la siguiente zona 'antes'."""
        tolerance = 1e-3
        before_zone = self._find_next_before_zone(current_start, prohibited_zones)
        if not before_zone:
            return None

        prev_end = self._find_zone_end_before(before_zone.start_m, prohibited_zones)
        if prev_end is None:
            return None

        corridor_end = before_zone.start_m - tolerance
        target = prev_end + splice_length
        target = min(target, corridor_end, candidate_end)
        if target - current_start < splice_length - tolerance:
            return None

        return target


    @staticmethod
    def _overlaps_prohibited_zone(start: float, end: float, zones: List[ProhibitedZone]) -> bool:
        for zone in zones:
            if max(start, zone.start_m) < min(end, zone.end_m):
                return True
        return False
    
    def _distribute_support_bars(self, diameter: str, count: int, coordinates: Dict,
                                position: str, hook_type: str, 
                                development_length: float) -> List[RebarDetail]:
        """Distribuye barras de apoyo en los extremos"""
        bars = []
        total_spans = len(coordinates.get('spans', []))
        
        if total_spans == 0:
            return bars
        
        # Longitud típica de barra de apoyo (25% de la luz promedio + desarrollo)
        avg_span_length = sum(span['length'] for span in coordinates['spans']) / total_spans
        support_bar_length = avg_span_length * 0.25 + development_length
        
        for i in range(count):
            bar_id = f"{'T' if position == 'top' else 'B'}{diameter.replace('#', '')}-A{i+1:02d}"
            
            # Alternar entre apoyos izquierdo y derecho
            if i % 2 == 0:
                start = 0
                end = support_bar_length
                notes = "Apoyo izquierdo"
            else:
                start = coordinates['total_length'] - support_bar_length
                end = coordinates['total_length']
                notes = "Apoyo derecho"
            
            bar = RebarDetail(
                id=bar_id,
                diameter=diameter,
                position=position,
                type='support',
                length_m=support_bar_length,
                start_m=start,
                end_m=end,
                hook_type=hook_type,
                splices=None,
                quantity=1,
                development_length_m=development_length,
                notes=notes
            )
            bars.append(bar)
        
        return bars
    
    def _distribute_span_bars(self, diameter: str, count: int, coordinates: Dict,
                             position: str, hook_type: str, 
                             development_length: float, bar_type: str) -> List[RebarDetail]:
        """Distribuye barras en luces"""
        bars = []
        spans = coordinates.get('spans', [])
        
        if not spans:
            return bars
        
        # Para barras que entran al apoyo
        if bar_type == 'support_anchored':
            bar_length = spans[0]['length'] * 0.8  # 80% de la primera luz
            
            for i in range(min(count, 2)):  # Máximo 2 barras por configuración
                bar_id = f"{'T' if position == 'top' else 'B'}{diameter.replace('#', '')}-S{i+1:02d}"
                
                bar = RebarDetail(
                    id=bar_id,
                    diameter=diameter,
                    position=position,
                    type='support_anchored',
                    length_m=bar_length,
                    start_m=0,
                    end_m=bar_length,
                    hook_type=hook_type,
                    splices=None,
                    quantity=1,
                    development_length_m=development_length,
                    notes="Entra al apoyo (≥ Ld)"
                )
                bars.append(bar)
            
            # Si hay más barras, ponerlas en luces centrales
            remaining = count - len(bars)
            if remaining > 0:
                mid_span_bars = self._create_mid_span_bars(
                    diameter, remaining, spans, position, 
                    hook_type, development_length
                )
                bars.extend(mid_span_bars)
        
        # Para barras de luz (no ancladas)
        else:
            mid_span_bars = self._create_mid_span_bars(
                diameter, count, spans, position, 
                hook_type, development_length
            )
            bars.extend(mid_span_bars)
        
        return bars
    
    def _create_mid_span_bars(self, diameter: str, count: int, spans: List[Dict],
                             position: str, hook_type: str, 
                             development_length: float) -> List[RebarDetail]:
        """Crea barras para centros de luz"""
        bars = []
        
        # Usar la luz más larga para las barras
        longest_span = max(spans, key=lambda x: x['length'])
        bar_length = longest_span['length'] * 0.6  # 60% de la luz
        
        for i in range(count):
            bar_id = f"{'T' if position == 'top' else 'B'}{diameter.replace('#', '')}-M{i+1:02d}"
            
            # Centrar en la luz
            start = longest_span['start'] + (longest_span['length'] - bar_length) / 2
            
            bar = RebarDetail(
                id=bar_id,
                diameter=diameter,
                position=position,
                type='span',
                length_m=bar_length,
                start_m=start,
                end_m=start + bar_length,
                hook_type=hook_type,
                splices=None,
                quantity=1,
                development_length_m=development_length,
                notes="Centro de luz"
            )
            bars.append(bar)
        
        return bars
    
    def _apply_segment_reinforcement(self, beam_data: Dict, top_bars: List[RebarDetail],
                                    bottom_bars: List[RebarDetail], coordinates: Dict):
        """Aplica refuerzo adicional para segmentos específicos"""
        segment_reinforcements = beam_data.get('segment_reinforcements', [])
        
        for segment in segment_reinforcements:
            span_indexes = segment.get('span_indexes', [])
            if not span_indexes:
                continue
            
            # Aplicar refuerzo superior
            if segment.get('top_quantity') and segment.get('top_diameter'):
                self._add_segment_bars(
                    span_indexes, segment['top_quantity'], 
                    segment['top_diameter'], 'top', coordinates, top_bars
                )
            
            # Aplicar refuerzo inferior
            if segment.get('bottom_quantity') and segment.get('bottom_diameter'):
                self._add_segment_bars(
                    span_indexes, segment['bottom_quantity'], 
                    segment['bottom_diameter'], 'bottom', coordinates, bottom_bars
                )
    
    def _add_segment_bars(self, span_indexes: List[int], quantity: int, 
                         diameter: str, position: str, 
                         coordinates: Dict, bars_list: List[RebarDetail]):
        """Agrega barras para segmentos específicos"""
        spans = coordinates.get('spans', [])
        
        for span_idx in span_indexes:
            if 0 <= span_idx < len(spans):
                span = spans[span_idx]
                
                for i in range(quantity):
                    bar_id = f"{'T' if position == 'top' else 'B'}{diameter.replace('#', '')}-E{span_idx+1}-{i+1:02d}"
                    
                    # Barra que cubre todo el segmento
                    bar_length = span['length'] * 0.9  # 90% del segmento
                    start = span['start'] + span['length'] * 0.05  # Centrado
                    
                    bar = RebarDetail(
                        id=bar_id,
                        diameter=diameter,
                        position=position,
                        type='segment',
                        length_m=bar_length,
                        start_m=start,
                        end_m=start + bar_length,
                        hook_type='135',
                        splices=None,
                        quantity=1,
                        development_length_m=self.base_development_lengths.get(diameter, 0.6),
                        notes=f"Refuerzo segmento {span_idx+1}"
                    )
                    bars_list.append(bar)

    def _get_single_hook_length(self, diameter: str, hook_type: Optional[str]) -> float:
        if not hook_type:
            return 0.0
        hook_lengths = self.hook_length_table.get(diameter)
        if not hook_lengths:
            return 0.0
        length = hook_lengths.get(hook_type)
        if not length:
            return 0.0
        return float(length)

    def _apply_cover_and_hook_adjustments(
        self,
        bars: List[RebarDetail],
        total_length: float,
        edge_cover: float,
        max_bar_length: float,
    ) -> None:
        if not bars:
            return

        cover = max(self.min_edge_cover_m, edge_cover or 0.0)
        max_end = max(total_length - cover, cover)
        tolerance = 1e-3
        max_length = max(max_bar_length or 0.0, 0.0)

        for bar in bars:
            original_start = bar.start_m
            original_end = bar.end_m

            start = max(cover, min(original_start, max_end))
            end = max(cover, min(original_end, max_end))
            if end < start:
                start, end = end, start

            bar.start_m = start
            bar.end_m = end
            straight_length = max(end - start, 0.0)

            hook_length = self._get_single_hook_length(bar.diameter, bar.hook_type)
            start_hook = hook_length if hook_length and original_start <= cover + tolerance else 0.0
            end_hook = hook_length if hook_length and original_end >= total_length - cover - tolerance else 0.0
            total_with_hooks = straight_length + start_hook + end_hook

            if max_length > 0 and total_with_hooks > max_length + tolerance:
                # Trim the straight portion so hooks do not push the bar beyond stock limits
                allowed_straight = max(max_length - (start_hook + end_hook), 0.0)
                if allowed_straight + tolerance < straight_length:
                    bar.end_m = bar.start_m + allowed_straight
                    straight_length = max(bar.end_m - bar.start_m, 0.0)
                    total_with_hooks = straight_length + start_hook + end_hook

                if total_with_hooks > max_length + tolerance:
                    logger.warning(
                        "La barra %s requiere %.2fm (incluyendo ganchos) y excede la longitud máxima %.2fm",
                        bar.id,
                        total_with_hooks,
                        max_length,
                    )
                    total_with_hooks = max_length

            bar.length_m = total_with_hooks
    
    def _generate_material_list(self, all_bars: List[RebarDetail], 
                               beam_data: Dict) -> List[MaterialItem]:
        """Genera lista de materiales optimizada"""
        # Agrupar por diámetro
        by_diameter = defaultdict(list)
        for bar in all_bars:
            by_diameter[bar.diameter].append(bar)
        
        material_list = []
        max_length = beam_data.get('max_bar_length_m', 12.0)
        
        for diameter, bars in by_diameter.items():
            # Calcular longitudes totales
            total_length = sum(bar.length_m * bar.quantity for bar in bars)
            total_pieces = sum(bar.quantity for bar in bars)
            
            # Optimizar cortes
            commercial_lengths = self._optimize_cutting_stock(
                diameter, bars, max_length
            )
            
            # Calcular peso
            weight_per_m = self.rebar_weights.get(diameter, 0.0)
            total_weight = total_length * weight_per_m
            
            # Calcular desperdicio
            total_commercial_length = sum(
                cut['num_bars'] * cut['commercial_length'] 
                for cut in commercial_lengths
            )
            waste_percentage = 0
            if total_commercial_length > 0:
                waste = total_commercial_length - total_length
                waste_percentage = (waste / total_commercial_length) * 100
            
            item = MaterialItem(
                diameter=diameter,
                total_length_m=round(total_length, 2),
                pieces=total_pieces,
                weight_kg=round(total_weight, 1),
                commercial_lengths=commercial_lengths,
                waste_percentage=round(waste_percentage, 1)
            )
            material_list.append(item)
        
        return material_list
    
    def _optimize_cutting_stock(self, diameter: str, bars: List[RebarDetail], 
                               max_length: float) -> List[Dict[str, Any]]:
        """Algoritmo simplificado de cutting stock"""
        # Extraer longitudes y cantidades
        length_counts = []
        for bar in bars:
            for _ in range(bar.quantity):
                length_counts.append(bar.length_m)
        
        if not length_counts:
            return []
        
        # Ordenar de mayor a menor
        length_counts.sort(reverse=True)
        
        cuts = []
        remaining = length_counts.copy()
        
        while remaining:
            current_bar = max_length
            current_cuts = []
            
            i = 0
            while i < len(remaining):
                if remaining[i] <= current_bar:
                    current_cuts.append(remaining[i])
                    current_bar -= remaining[i]
                    remaining.pop(i)
                else:
                    i += 1
            
            if current_cuts:
                waste = max_length - sum(current_cuts)
                efficiency = (sum(current_cuts) / max_length) * 100 if max_length > 0 else 0
                
                cuts.append({
                    'commercial_length': max_length,
                    'cut_lengths': current_cuts,
                    'num_bars': 1,
                    'waste_m': waste,
                    'efficiency': efficiency
                })
                continue

            # Si ninguna barra cabe en la longitud comercial disponible,
            # registrar la barra más larga como pieza individual para evitar bucles infinitos.
            long_bar = remaining.pop(0)
            cuts.append({
                'commercial_length': max(long_bar, max_length),
                'cut_lengths': [long_bar],
                'num_bars': 1,
                'waste_m': max(max_length - long_bar, 0),
                'efficiency': 100 if long_bar >= max_length else (long_bar / max_length) * 100
            })
        
        return cuts
    
    def _validate_nsr10(self, beam_data: Dict, top_bars: List[RebarDetail],
                       bottom_bars: List[RebarDetail], prohibited_zones: List[ProhibitedZone],
                       continuous_bars: Dict) -> List[str]:
        """Realiza validaciones NSR-10 y retorna advertencias"""
        warnings: List[str] = []

        top_continuous = sum(1 for bar in top_bars if bar.type == 'continuous')
        bottom_continuous = sum(1 for bar in bottom_bars if bar.type == 'continuous')

        if top_continuous < 2:
            warnings.append("NSR-10 C.21.5.2.1: Mínimo 2 barras superiores continuas requeridas")
        if bottom_continuous < 2:
            warnings.append("NSR-10 C.21.5.2.1: Mínimo 2 barras inferiores continuas requeridas")

        # 2. Empalmes fuera de zonas prohibidas
        for bar in top_bars + bottom_bars:
            if not bar.splices:
                continue
            for splice in bar.splices:
                zone = self._find_overlapping_zone(splice['start'], splice['end'], prohibited_zones)
                if zone:
                    warnings.append(
                        f"Barra {bar.id}: Empalme en zona prohibida ({zone.start_m:.2f}-{zone.end_m:.2f}m)"
                    )
                    break
        
        # 3. Verificar longitudes de desarrollo
        for bar in top_bars + bottom_bars:
            if bar.development_length_m and bar.length_m < bar.development_length_m:
                warnings.append(
                    f"Barra {bar.id}: Longitud insuficiente para desarrollo "
                    f"(necesita {bar.development_length_m:.2f}m, tiene {bar.length_m:.2f}m)"
                )
        
        # 4. Verificar clase de disipación de energía
        energy_class = beam_data.get('energy_dissipation_class', 'DES')
        if energy_class == 'DES':
            # Validar ganchos para alta disipación
            for bar in top_bars + bottom_bars:
                if bar.type == 'continuous' and bar.hook_type not in ['135', '180']:
                    warnings.append(
                        f"Barra {bar.id}: En DES se recomiendan ganchos de 135° o 180° "
                        f"(actual: {bar.hook_type}°)"
                    )
        
        # 5. Verificar relación de cantidades
        total_top = sum(bar.quantity for bar in top_bars)
        total_bottom = sum(bar.quantity for bar in bottom_bars)
        
        if total_top == 0:
            warnings.append("No se definieron barras superiores")
        if total_bottom == 0:
            warnings.append("No se definieron barras inferiores")
        
        return warnings