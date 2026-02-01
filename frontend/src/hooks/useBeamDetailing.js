import { useState, useCallback } from 'react';
import axios from 'axios';

export const useBeamDetailing = () => {
  const [detailingResults, setDetailingResults] = useState(null);
  const [isComputing, setIsComputing] = useState(false);
  const [error, setError] = useState(null);

  const computeDetailing = useCallback(async (beamData) => {
    setIsComputing(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No hay sesión activa');
      }

      // Preparar datos para el cálculo
      const detailingRequest = {
        span_geometries: beamData.span_geometries || [],
        axis_supports: beamData.axis_supports || [],
        top_bars_config: beamData.top_bars_config || [],
        bottom_bars_config: beamData.bottom_bars_config || [],
        segment_reinforcements: beamData.segment_reinforcements || [],
        has_initial_cantilever: beamData.has_initial_cantilever || false,
        has_final_cantilever: beamData.has_final_cantilever || false,
        cover_cm: beamData.cover_cm || 4,
        max_rebar_length_m: beamData.max_rebar_length_m || '12m',
        hook_type: beamData.hook_type || '135',
        energy_dissipation_class: beamData.energy_dissipation_class || 'DES',
        concrete_strength: beamData.concrete_strength || '21 MPa (3000 psi)',
        reinforcement: beamData.reinforcement || '420 MPa (Grado 60)',
        lap_splice_length_min_m: beamData.lap_splice_length_min_m || 0.75
      };

      const response = await axios.post(
        '/api/v1/tools/despiece/compute-detailing',
        detailingRequest,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.data.success) {
        setDetailingResults(response.data.results);
        return { success: true, data: response.data.results };
      } else {
        throw new Error(response.data.message || 'Error en el cálculo');
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Error desconocido';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setIsComputing(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setDetailingResults(null);
    setError(null);
  }, []);

  return {
    detailingResults,
    isComputing,
    error,
    computeDetailing,
    clearResults
  };
};

// Función auxiliar para extraer datos del formulario
export const extractBeamData = (formValues) => {
  return {
    span_geometries: formValues.span_geometries || [],
    axis_supports: formValues.axis_supports || [],
    top_bars_config: formValues.top_bars_config || [],
    bottom_bars_config: formValues.bottom_bars_config || [],
    segment_reinforcements: formValues.segment_reinforcements || [],
    has_initial_cantilever: formValues.has_initial_cantilever || false,
    has_final_cantilever: formValues.has_final_cantilever || false,
    cover_cm: formValues.cover_cm || 4,
    max_rebar_length_m: formValues.max_rebar_length_m || '12m',
    hook_type: formValues.hook_type || '135',
    energy_dissipation_class: formValues.energy_dissipation_class || 'DES',
    concrete_strength: formValues.concrete_strength || '21 MPa (3000 psi)',
    reinforcement: formValues.reinforcement || '420 MPa (Grado 60)',
    lap_splice_length_min_m: formValues.lap_splice_length_min_m || 0.75,
    element_level: formValues.element_level,
    beam_total_length_m: formValues.beam_total_length_m,
    project_name: formValues.project_name,
    beam_label: formValues.beam_label
  };
};