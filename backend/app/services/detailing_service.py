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

class BeamDetailingService:
    """Servicio para cálculo de despiece automático según NSR-10"""
    
    def __init__(self):
        # Factores NSR-10 según clase de disipación de energía
        self.energy_factors = {
            'DES': 1.3,  # Alta disipación - Empalmes Clase B
            'DMO': 1.0,  # Disipación moderada
            'DMI': 1.0   # Disipación mínima
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
        
        try:
            logger.info("Iniciando cálculo de despiece NSR-10")
            
            # 1. Validar y preprocesar datos
            beam_data = self._preprocess_data(data)
            if not beam_data:
                return DetailingResponse(
                    success=False,
                    message="Datos de entrada inválidos"
                )
            
            # 2. Calcular geometría de la viga
            coordinates = self._calculate_coordinates(beam_data)
            
            # 3. Identificar barras continuas obligatorias (NSR-10 C.21.5.2.1)
            continuous_bars = self._identify_continuous_bars(beam_data)
            
            # 4. Calcular zonas prohibidas para empalmes (NSR-10 C.21.5.3.2)
            prohibited_zones = self._calculate_prohibited_zones(coordinates, beam_data)
            
            # 5. Calcular longitud de desarrollo ajustada
            development_lengths = self._calculate_development_lengths(beam_data)
            
            # 6. Generar detalle de barras superiores
            top_bars = self._detail_top_bars(
                beam_data, coordinates, prohibited_zones, 
                continuous_bars, development_lengths
            )
            
            # 7. Generar detalle de barras inferiores
            bottom_bars = self._detail_bottom_bars(
                beam_data, coordinates, prohibited_zones,
                continuous_bars, development_lengths
            )
            
            # 8. Aplicar refuerzo de segmentos específicos
            if beam_data.get('segment_reinforcements'):
                self._apply_segment_reinforcement(
                    beam_data, top_bars, bottom_bars, coordinates
                )
            
            # 9. Optimizar cortes y generar lista de materiales
            material_list = self._generate_material_list(
                top_bars + bottom_bars, beam_data
            )
            
            # 10. Validaciones NSR-10
            warnings = self._validate_nsr10(
                beam_data, top_bars, bottom_bars, 
                prohibited_zones, continuous_bars
            )
            
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
            
            return DetailingResponse(
                success=True,
                results=results,
                computation_time_ms=computation_time,
                message="Despiece calculado exitosamente según NSR-10"
            )
            
        except Exception as e:
            logger.error(f"Error en cálculo de despiece: {str(e)}", exc_info=True)
            return DetailingResponse(
                success=False,
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
        zones = []
        d = beam_data.get('effective_depth_m', 0.5)
        
        for face in coordinates['faces']:
            if face['type'] == 'support_face':
                support_half_width = face['width'] / 2
                prohibited_distance = max(2 * d, support_half_width)
                
                # No permitir que la zona se extienda más allá del centro de la luz adyacente
                end_limit = coordinates['total_length']
                for span in coordinates['spans']:
                    if abs(span['start'] - face['x']) < 0.01:  # Luz después de este apoyo
                        end_limit = min(end_limit, span['start'] + span['length'] / 2)
                        break
                
                zone_end = min(face['x'] + prohibited_distance, end_limit)
                
                if zone_end > face['x']:  # Solo crear zona si tiene longitud
                    zone = ProhibitedZone(
                        start_m=face['x'],
                        end_m=zone_end,
                        type='no_splice_zone',
                        description=f"No empalmar: {prohibited_distance*100:.0f} cm desde {face.get('label', f'Eje {face['support_index']+1}')}",
                        support_index=face['support_index']
                    )
                    zones.append(zone)
        
        return zones
    
    def _calculate_development_lengths(self, beam_data: Dict) -> Dict[str, float]:
        """Calcula longitudes de desarrollo ajustadas según NSR-10 C.12.2"""
        development_lengths = {}
        concrete_strength = beam_data.get('concrete_strength', '21 MPa (3000 psi)')
        reinforcement = beam_data.get('reinforcement', '420 MPa (Grado 60)')
        
        fc_factor = self.fc_factors.get(concrete_strength, 1.0)
        fy_factor = self.fy_factors.get(reinforcement, 1.0)
        energy_factor = self.energy_factors.get(beam_data.get('energy_dissipation_class', 'DES'), 1.0)
        
        for diameter, base_length in self.base_development_lengths.items():
            # Longitud básica ajustada por f'c y fy
            adjusted_length = base_length * fc_factor * fy_factor
            
            # Para empalmes clase B en zonas sísmicas
            splice_length = adjusted_length * energy_factor
            
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
                bars.append(bar)
            
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
                splices = self._calculate_splices(
                    total_length=coordinates['total_length'],
                    max_bar_length=max_length,
                    prohibited_zones=prohibited_zones,
                    splice_length=dev_info['splice']
                )
                
                bar = RebarDetail(
                    id=bar_id,
                    diameter=diameter,
                    position='bottom',
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
                bars.append(bar)
            
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
                        quantity=1,
                        development_length_m=self.base_development_lengths.get(diameter, 0.6),
                        notes=f"Refuerzo segmento {span_idx+1}"
                    )
                    bars_list.append(bar)
    
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
                efficiency = (sum(current_cuts) / max_length) * 100
                
                cuts.append({
                    'commercial_length': max_length,
                    'cut_lengths': current_cuts,
                    'num_bars': 1,
                    'waste_m': waste,
                    'efficiency': efficiency
                })
        
        return cuts
    
    def _validate_nsr10(self, beam_data: Dict, top_bars: List[RebarDetail],
                       bottom_bars: List[RebarDetail], prohibited_zones: List[ProhibitedZone],
                       continuous_bars: Dict) -> List[str]:
        """Realiza validaciones NSR-10 y retorna advertencias"""
        warnings = []
        
        # 1. Verificar barras continuas mínimas (C.21.5.2.1)
        top_continuous = sum(1 for bar in top_bars if bar.type == 'continuous')
        bottom_continuous = sum(1 for bar in bottom_bars if bar.type == 'continuous')
        
        if top_continuous < 2:
            warnings.append("NSR-10 C.21.5.2.1: Mínimo 2 barras superiores continuas requeridas")
        if bottom_continuous < 2:
            warnings.append("NSR-10 C.21.5.2.1: Mínimo 2 barras inferiores continuas requeridas")
        
        # 2. Verificar empalmes en zonas prohibidas (C.21.5.3.2)
        for bar in top_bars + bottom_bars:
            if bar.splices:
                for splice in bar.splices:
                    for zone in prohibited_zones:
                        if zone.start_m <= splice['start'] <= zone.end_m:
                            warnings.append(
                                f"Barra {bar.id}: Empalme en zona prohibida "
                                f"({zone.start_m:.2f}-{zone.end_m:.2f}m) - {zone.description}"
                            )
        
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