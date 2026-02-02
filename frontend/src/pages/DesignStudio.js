import React, { useEffect, useMemo, useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import BlockIdentification from './DesignStudioSections/BlockIdentification';
import BlockGeometrySupports from './DesignStudioSections/BlockGeometrySupports';
import BlockReinforcement from './DesignStudioSections/BlockReinforcement';
import DespieceExportPanel from './DesignStudioSections/DespieceExportPanel';
import {
  MAX_BAR_LENGTH_OPTIONS,
  getEnergyOptions,
  getHookOptionsForClass,
  getDiameterOptions,
  validateNSR10,
} from '../utils/nsr10Constants';
import { useBeamDetailing, extractBeamData } from '../hooks/useBeamDetailing';
import apiClient from '../utils/apiClient';
import { getAccessToken, getRefreshToken } from '../utils/auth';
import BeamDetailingView from './DesignStudioSections/BeamDetailingView';
import {
  DEFAULT_STIRRUP_DIAMETER,
  DEFAULT_STIRRUP_HOOK_TYPE,
  calculateEffectiveDepth,
  calculateSpacingForZone,
  estimateStirrupTotalLengthCm,
} from '../utils/stirrups';


const energyOptions = getEnergyOptions();
const lengthOptions = MAX_BAR_LENGTH_OPTIONS;
const diameterOptions = getDiameterOptions();
const DEFAULT_ENERGY_CLASS = 'DES';
const defaultHookOptions = getHookOptionsForClass(DEFAULT_ENERGY_CLASS);
const STIRRUP_TYPE_OPTIONS = [
  { value: 'C', label: 'Estribo en "C"' },
  { value: 'S', label: 'Estribo en "S"' },
];
const STIRRUP_TYPE_VALUES = STIRRUP_TYPE_OPTIONS.map((option) => option.value);
const LAP_SPLICE_FC_MAP = {
  '21 MPa (3000 psi)': 'fc_21_mpa_m',
  '24 MPa (3500 psi)': 'fc_24_mpa_m',
  '28 MPa (4000 psi)': 'fc_28_mpa_m',
  '32 MPa (4600 psi)': 'fc_28_mpa_m',
};
const barGroupSchema = z.object({
  quantity: z.coerce.number().int().min(1, 'Cantidad mínima 1'),
  diameter: z.enum(diameterOptions),
});

const optionalPositiveInt = z.preprocess(
  (value) => {
    if (value === '' || value === null) {
      return undefined;
    }
    if (typeof value === 'number' && Number.isNaN(value)) {
      return undefined;
    }
    return value;
  },
  z.coerce.number().int().min(1, 'Cantidad mínima 1').optional()
);

const optionalDiameter = z.preprocess(
  (value) => (value === '' || value === null ? undefined : value),
  z.enum(diameterOptions).optional()
);

const segmentReinforcementSchema = z
  .object({
    span_indexes: z.array(z.coerce.number().int().min(0)).min(1, 'Selecciona al menos un tramo'),
    top_quantity: optionalPositiveInt,
    top_diameter: optionalDiameter,
    bottom_quantity: optionalPositiveInt,
    bottom_diameter: optionalDiameter,
  })
  .refine(
    (data) => {
      const hasTop = data.top_quantity !== undefined || data.top_diameter !== undefined;
      return !hasTop || (data.top_quantity !== undefined && data.top_diameter !== undefined);
    },
    {
      message: 'Completa cantidad y diámetro para el refuerzo superior',
      path: ['top_quantity'],
    }
  )
  .refine(
    (data) => {
      const hasBottom = data.bottom_quantity !== undefined || data.bottom_diameter !== undefined;
      return !hasBottom || (data.bottom_quantity !== undefined && data.bottom_diameter !== undefined);
    },
    {
      message: 'Completa cantidad y diámetro para el refuerzo inferior',
      path: ['bottom_quantity'],
    }
  )
  .refine(
    (data) => {
      const hasTop = data.top_quantity !== undefined && data.top_diameter !== undefined;
      const hasBottom = data.bottom_quantity !== undefined && data.bottom_diameter !== undefined;
      return hasTop || hasBottom;
    },
    {
      message: 'Define al menos un refuerzo superior o inferior',
      path: ['span_indexes'],
    }
  );

const stirrupSchema = z.object({
  additional_branches: z.coerce.number().int().min(0, 'Cantidad mínima 0'),
  stirrup_type: z.enum(STIRRUP_TYPE_VALUES),
});

const elementLevelSchema = z.preprocess(
  (value) => {
    if (typeof value === 'number' && Number.isNaN(value)) {
      return undefined;
    }
    return value;
  },
  z
    .number({ required_error: 'Ingresa el nivel', invalid_type_error: 'Ingresa el nivel' })
    .refine((val) => Number.isFinite(val), 'Ingresa el nivel')
    .transform((val) => Number(val.toFixed(2)))
);

const formSchema = z.object({
  project_name: z.string().min(1, 'Indica el proyecto'),
  beam_label: z.string().min(1, 'Identifica la viga'),
  element_identifier: z.string().min(1, 'Campo obligatorio'),
  element_level: elementLevelSchema,
  element_quantity: z.coerce.number().int().min(1, 'Cantidad mínima 1'),
  top_bars_config: z.array(barGroupSchema).min(1, 'Agrega al menos un grupo de barras superiores'),
  bottom_bars_config: z.array(barGroupSchema).min(1, 'Agrega al menos un grupo de barras inferiores'),
  max_rebar_length_m: z.enum(lengthOptions),
  beam_total_length_m: z.coerce.number().nonnegative('Longitud total inválida'),
  has_initial_cantilever: z.boolean(),
  has_final_cantilever: z.boolean(),
  hook_type: z.enum(defaultHookOptions.map((opt) => opt.value)),
  cover_cm: z.coerce.number().int().min(1, 'Define el recubrimiento en cm'),
  span_geometries: z
    .array(
      z.object({
        clear_span_between_supports_m: z.coerce
          .number()
          .nonnegative('Define la luz libre'),
        section_base_cm: z.coerce.number().int().positive('Ingresa la base en cm'),
        section_height_cm: z.coerce.number().int().positive('Ingresa la altura en cm'),
      })
    )
    .min(1, 'Configura al menos una luz'),
  axis_supports: z
    .array(
      z.object({
        label: z.string().optional(),
        support_width_cm: z.coerce.number().int().nonnegative('Ancho inválido').default(0),
      })
    )
    .optional(),
  span_count: z.coerce.number().int().positive('Ingresa un número entero positivo'),
  segment_reinforcements: z.array(segmentReinforcementSchema).optional(),
  stirrups_config: z.array(stirrupSchema).min(1, 'Agrega al menos una zona'),
  energy_dissipation_class: z.enum(energyOptions),
  concrete_strength: z.string().min(1, 'Selecciona f’c'),
  reinforcement: z.string().min(1, 'Selecciona fy'),
});

const calculateBeamTotalLength = (spans, supports) => {
  const spanSum = (spans || []).reduce((sum, span) => sum + Number(span?.clear_span_between_supports_m || 0), 0);
  const supportSum = (supports || []).reduce((sum, support) => sum + Number(support?.support_width_cm || 0) / 100, 0);
  const total = spanSum + supportSum;
  return Number.isFinite(total) ? Number(total.toFixed(2)) : 0;
};

const formatDimensionValue = (value) => {
  if (value === undefined || value === null) {
    return null;
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return null;
  }
  return Number(numeric.toFixed(2));
};

const defaultValues = {
  project_name: 'Centro Cultural La Estación',
  beam_label: 'VIGA-E3-12',
  element_identifier: 'VIGA-E3-12',
  element_level: 3.52,
  element_quantity: 1,
  top_bars_config: [
    { quantity: 2, diameter: '#5' },
    { quantity: 2, diameter: '#6' },
  ],
  bottom_bars_config: [{ quantity: 2, diameter: '#5' }],
  segment_reinforcements: [],
  max_rebar_length_m: '9m',
  has_initial_cantilever: false,
  has_final_cantilever: false,
  span_geometries: [
    { clear_span_between_supports_m: 3.2, section_base_cm: 30, section_height_cm: 45 },
    { clear_span_between_supports_m: 4.0, section_base_cm: 30, section_height_cm: 45 },
    { clear_span_between_supports_m: 3.2, section_base_cm: 30, section_height_cm: 45 },
  ],
  hook_type: '180',
  cover_cm: 4,
  axis_supports: [
    { label: 'EJE 3', support_width_cm: 35 },
    { label: 'EJE 4', support_width_cm: 35 },
    { label: 'EJE 5', support_width_cm: 35 },
    { label: 'EJE 6', support_width_cm: 35 },
  ],
  span_count: 3,
  stirrups_config: [
    { additional_branches: 0, stirrup_type: 'C' },
    { additional_branches: 0, stirrup_type: 'S' },
  ],
  energy_dissipation_class: DEFAULT_ENERGY_CLASS,
  concrete_strength: '21 MPa (3000 psi)',
  reinforcement: '420 MPa (Grado 60)',
};

defaultValues.beam_total_length_m = calculateBeamTotalLength(defaultValues.span_geometries, defaultValues.axis_supports);

const DesignStudio = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastDesign, setLastDesign] = useState(null);
  const [hookOptions, setHookOptions] = useState(() => defaultHookOptions);
  const [showDetailing, setShowDetailing] = useState(false);
  const [detailingResults, setDetailingResults] = useState(null);
  const [lapSpliceLookup, setLapSpliceLookup] = useState(null);
  const [lapSpliceLoading, setLapSpliceLoading] = useState(false);

  const { isComputing: isDetailingComputing, error: detailingError, computeDetailing } = useBeamDetailing();

  const {
    control,
    handleSubmit,
    register,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(formSchema),
    defaultValues,
    mode: 'onBlur',
  });

  const {
    fields: stirrupFields,
    append: appendStirrup,
    remove: removeStirrup,
  } = useFieldArray({ control, name: 'stirrups_config' });

  const {
    fields: topBarFields,
    append: appendTopBarGroup,
    remove: removeTopBarGroup,
  } = useFieldArray({ control, name: 'top_bars_config' });

  const {
    fields: bottomBarFields,
    append: appendBottomBarGroup,
    remove: removeBottomBarGroup,
  } = useFieldArray({ control, name: 'bottom_bars_config' });

  const {
    fields: segmentReinforcementFields,
    append: appendSegmentReinforcement,
    remove: removeSegmentReinforcement,
  } = useFieldArray({ control, name: 'segment_reinforcements' });

  const { fields: axisSupportFields, replace: replaceAxisSupports } = useFieldArray({ control, name: 'axis_supports' });
  const { fields: spanGeometryFields, replace: replaceSpanGeometries } = useFieldArray({ control, name: 'span_geometries' });

  const energyClass = watch('energy_dissipation_class');
  const selectedLength = watch('max_rebar_length_m');
  const watchHookType = watch('hook_type');
  const watchStirrups = watch('stirrups_config');
  const watchSpanCount = watch('span_count');
  const watchAxisSupports = watch('axis_supports');
  const watchSpanGeometries = watch('span_geometries');
  const watchInitialCantilever = watch('has_initial_cantilever');
  const watchFinalCantilever = watch('has_final_cantilever');
  const watchTopBarGroups = watch('top_bars_config');
  const watchBottomBarGroups = watch('bottom_bars_config');
  const watchSegmentReinforcements = watch('segment_reinforcements');
  const watchBeamTotalLength = watch('beam_total_length_m');
  const watchConcreteStrength = watch('concrete_strength');
  const watchCoverCm = watch('cover_cm');
  const watchProjectName = watch('project_name');
  const watchBeamLabelField = watch('beam_label');

  const activeProjectName =
    lastDesign?.despiece_viga?.project_name || lastDesign?.title || watchProjectName;
  const activeBeamLabel = lastDesign?.despiece_viga?.beam_label || watchBeamLabelField;
  const nsrWarnings = useMemo(
    () => validateNSR10({ energy_dissipation_class: energyClass, hook_type: watchHookType }),
    [energyClass, watchHookType]
  );
  const summarizeBarConfig = (config) => {
    if (!Array.isArray(config) || config.length === 0) {
      return {
        totalBars: 0,
        groupsCount: 0,
        diametersLabel: 'Sin Φ definidos',
        detailLabel: 'Sin configuración activa',
      };
    }

    const sanitizedGroups = config
      .map((group) => ({
        quantity: Number(group?.quantity) || 0,
        diameter: group?.diameter || null,
      }))
      .filter((group) => group.quantity > 0 && group.diameter);

    const totalBars = sanitizedGroups.reduce((sum, group) => sum + group.quantity, 0);
    const groupsCount = sanitizedGroups.length;
    const diameters = [...new Set(sanitizedGroups.map((group) => group.diameter))];
    const detailLabel = groupsCount
      ? sanitizedGroups.map((group) => `${group.quantity}x${group.diameter}`).join(' + ')
      : 'Sin configuración activa';

    return {
      totalBars,
      groupsCount,
      diametersLabel: diameters.length ? diameters.join(', ') : 'Sin Φ definidos',
      detailLabel,
    };
  };
  const topBarsGroupError = errors.top_bars_config?.root?.message || errors.top_bars_config?.message;
  const bottomBarsGroupError = errors.bottom_bars_config?.root?.message || errors.bottom_bars_config?.message;
  const totalTopBars = useMemo(
    () =>
      (watchTopBarGroups || []).reduce((sum, group) => {
        const qty = Number(group?.quantity);
        return sum + (Number.isFinite(qty) ? qty : 0);
      }, 0),
    [watchTopBarGroups]
  );
  const totalBottomBars = useMemo(
    () =>
      (watchBottomBarGroups || []).reduce((sum, group) => {
        const qty = Number(group?.quantity);
        return sum + (Number.isFinite(qty) ? qty : 0);
      }, 0),
    [watchBottomBarGroups]
  );
  const topBarCharacteristics = useMemo(() => summarizeBarConfig(watchTopBarGroups), [watchTopBarGroups]);
  const bottomBarCharacteristics = useMemo(
    () => summarizeBarConfig(watchBottomBarGroups),
    [watchBottomBarGroups]
  );
  const segmentReinforcementsError =
    errors.segment_reinforcements?.root?.message || errors.segment_reinforcements?.message;
  const beamTotalLength = calculateBeamTotalLength(watchSpanGeometries, watchAxisSupports);
  const spanOptions = useMemo(
    () =>
      (watchSpanGeometries || []).map((span, index) => {
        const lengthValue = formatDimensionValue(span?.clear_span_between_supports_m);
        return {
          value: index,
          label: `Tramo ${index + 1}`,
          lengthLabel: lengthValue !== null ? `${lengthValue} m` : null,
        };
      }),
    [watchSpanGeometries]
  );
  const elementLevelField = register('element_level', { valueAsNumber: true });

  useEffect(() => {
    if (!energyClass) {
      return;
    }
    const allowedOptions = getHookOptionsForClass(energyClass);
    setHookOptions(allowedOptions);
    if (allowedOptions.length && !allowedOptions.some((option) => option.value === watchHookType)) {
      setValue('hook_type', allowedOptions[0].value, { shouldDirty: true });
    }
  }, [energyClass, watchHookType, setValue]);

  useEffect(() => {
    const spanTotal = Number(watchSpanCount) || 0;
    const requiredAxes = Math.max(spanTotal + 1, 0);
    const currentSupports = watchAxisSupports || [];

    if (currentSupports.length === requiredAxes) {
      return;
    }

    const nextSupports = Array.from({ length: requiredAxes }, (_, index) => {
      const existing = currentSupports[index];
      return existing ?? { label: '', support_width_cm: 0 };
    });
    replaceAxisSupports(nextSupports);
  }, [watchSpanCount, watchAxisSupports, replaceAxisSupports]);

  useEffect(() => {
    const spanTotal = Number(watchSpanCount) || 0;
    const requiredSpans = Math.max(spanTotal, 0);
    const currentSpans = watchSpanGeometries || [];

    if (currentSpans.length === requiredSpans) {
      return;
    }

    const nextSpans = Array.from({ length: requiredSpans }, (_, index) => {
      const existing = currentSpans[index];
      return (
        existing ?? {
          clear_span_between_supports_m: 0,
          section_base_cm: 0,
          section_height_cm: 0,
        }
      );
    });
    replaceSpanGeometries(nextSpans);
  }, [watchSpanCount, watchSpanGeometries, replaceSpanGeometries]);

  useEffect(() => {
    if (!Array.isArray(watchSegmentReinforcements) || !Array.isArray(watchSpanGeometries)) {
      return;
    }
    const totalSpans = watchSpanGeometries.length;
    watchSegmentReinforcements.forEach((reinforcement, index) => {
      const current = Array.isArray(reinforcement?.span_indexes) ? reinforcement.span_indexes : [];
      if (totalSpans === 0) {
        if (current.length > 0) {
          setValue(`segment_reinforcements.${index}.span_indexes`, [], { shouldDirty: true });
        }
        return;
      }
      const filtered = current.filter((spanIndex) => spanIndex >= 0 && spanIndex < totalSpans);
      if (filtered.length !== current.length) {
        setValue(`segment_reinforcements.${index}.span_indexes`, filtered, { shouldDirty: true });
      }
    });
  }, [watchSegmentReinforcements, watchSpanGeometries, setValue]);

  useEffect(() => {
    if (!Array.isArray(watchAxisSupports) || watchAxisSupports.length === 0) {
      return;
    }

    if (watchInitialCantilever) {
      const current = Number(watchAxisSupports[0]?.support_width_cm);
      if (current !== 0) {
        setValue('axis_supports.0.support_width_cm', 0, { shouldDirty: true });
      }
    }

    if (watchFinalCantilever) {
      const lastIndex = watchAxisSupports.length - 1;
      if (lastIndex >= 0) {
        const current = Number(watchAxisSupports[lastIndex]?.support_width_cm);
        if (current !== 0) {
          setValue(`axis_supports.${lastIndex}.support_width_cm`, 0, { shouldDirty: true });
        }
      }
    }
  }, [watchAxisSupports, watchInitialCantilever, watchFinalCantilever, setValue]);

  useEffect(() => {
    register('beam_total_length_m', { valueAsNumber: true });
  }, [register]);

  useEffect(() => {
    let isMounted = true;
    const fetchLapSpliceTable = async () => {
      setLapSpliceLoading(true);
      try {
        const response = await apiClient.get('/api/v1/tools/rebar/lap-splice-lengths');
        if (!isMounted) {
          return;
        }
        const lookup = (response.data || []).reduce((acc, item) => {
          const mark = item.bar_mark?.startsWith('#') ? item.bar_mark : `#${item.bar_mark || ''}`;
          if (!mark || mark === '#') {
            return acc;
          }
          acc[mark] = {
            fc_21_mpa_m: Number(item.fc_21_mpa_m),
            fc_24_mpa_m: Number(item.fc_24_mpa_m),
            fc_28_mpa_m: Number(item.fc_28_mpa_m),
          };
          return acc;
        }, {});
        setLapSpliceLookup(lookup);
      } catch (error) {
        console.error('No se pudo cargar la tabla de traslapos', error);
        if (isMounted) {
          setLapSpliceLookup(null);
        }
      } finally {
        if (isMounted) {
          setLapSpliceLoading(false);
        }
      }
    };

    fetchLapSpliceTable();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!Number.isFinite(beamTotalLength)) {
      return;
    }
    const nextValue = Number(beamTotalLength.toFixed(2));
    const currentValue = Number(watchBeamTotalLength);
    if (Number.isFinite(currentValue) && Math.abs(currentValue - nextValue) < 0.001) {
      return;
    }
    setValue('beam_total_length_m', nextValue, { shouldDirty: true });
  }, [beamTotalLength, watchBeamTotalLength, setValue]);

  const detailingStirrupsSummary = detailingResults?.stirrups_summary;
  const stirrupSegmentsByZone = useMemo(() => {
    if (!detailingStirrupsSummary?.zone_segments) {
      return { confined: [], non_confined: [] };
    }
    return (detailingStirrupsSummary.zone_segments || []).reduce(
      (acc, segment) => {
        if (segment.zone_type === 'confined') {
          acc.confined.push(segment);
        } else {
          acc.non_confined.push(segment);
        }
        return acc;
      },
      { confined: [], non_confined: [] }
    );
  }, [detailingStirrupsSummary]);
  const stirrupEstimatedTotal = useMemo(() => {
    const segments = detailingStirrupsSummary?.zone_segments;
    if (!Array.isArray(segments) || segments.length === 0) {
      return null;
    }
    const total = segments.reduce((sum, segment) => {
      const value = Number(segment?.estimated_count || 0);
      return sum + (Number.isFinite(value) ? value : 0);
    }, 0);
    return total;
  }, [detailingStirrupsSummary]);

  const stirrupBaseSpecs = useMemo(() => {
    const coverValue = Number(watchCoverCm) || 0;
    if (!Array.isArray(watchSpanGeometries)) {
      return [];
    }
    return watchSpanGeometries.map((span, index) => {
      const baseCm = Number(span?.section_base_cm) || 0;
      const sectionHeightCm = Number(span?.section_height_cm) || 0;
      const effectiveDepth = calculateEffectiveDepth(sectionHeightCm, coverValue);
      const stirrupWidthCm = Math.max(baseCm - 2 * coverValue, 0);
      const stirrupHeightCm = Math.max(sectionHeightCm - 2 * coverValue, 0);
      const { totalLengthCm, hookLengthCm } = estimateStirrupTotalLengthCm(stirrupWidthCm, stirrupHeightCm);
      return {
        label: `Luz ${index + 1}`,
        stirrupWidthCm,
        stirrupHeightCm,
        effectiveDepthCm: effectiveDepth * 100,
        spacingConfinedCm: calculateSpacingForZone(effectiveDepth, 'confined') * 100,
        spacingNonConfinedCm: calculateSpacingForZone(effectiveDepth, 'non_confined') * 100,
        stirrupTotalLengthCm: totalLengthCm,
        stirrupHookLengthCm: hookLengthCm,
      };
    });
  }, [watchSpanGeometries, watchCoverCm]);

  const spanOverview = useMemo(() => {
    const totalSpans = Number(watchSpanCount) || 0;
    let cantileverLabel = 'Sin voladizos';
    if (watchInitialCantilever && watchFinalCantilever) {
      cantileverLabel = 'Inicial y final';
    } else if (watchInitialCantilever) {
      cantileverLabel = 'Solo inicial';
    } else if (watchFinalCantilever) {
      cantileverLabel = 'Solo final';
    }

    return {
      totalSpans,
      totalLengthValue: beamTotalLength,
      totalLengthLabel: beamTotalLength.toFixed(2),
      cantileverLabel,
    };
  }, [watchSpanCount, watchInitialCantilever, watchFinalCantilever, beamTotalLength]);

  const computedLapSpliceLength = useMemo(() => {
    if (!lapSpliceLookup) {
      return null;
    }
    const fcKey = LAP_SPLICE_FC_MAP[watchConcreteStrength] || 'fc_21_mpa_m';
    const collectDiameters = (groups) => {
      const result = new Set();
      (groups || []).forEach((group) => {
        if (!group?.diameter) {
          return;
        }
        const mark = group.diameter.startsWith('#') ? group.diameter : `#${group.diameter}`;
        result.add(mark);
      });
      return result;
    };

    const topDiameters = collectDiameters(watchTopBarGroups);
    const bottomDiameters = collectDiameters(watchBottomBarGroups);
    const uniqueDiameters = new Set([...topDiameters, ...bottomDiameters]);

    if (uniqueDiameters.size === 0) {
      return null;
    }

    const candidateLengths = Array.from(uniqueDiameters)
      .map((mark) => lapSpliceLookup[mark]?.[fcKey])
      .filter((value) => Number.isFinite(value));

    if (candidateLengths.length === 0) {
      return null;
    }

    return Number(Math.max(...candidateLengths).toFixed(2));
  }, [lapSpliceLookup, watchConcreteStrength, watchTopBarGroups, watchBottomBarGroups]);

  const lapSpliceChecklistLabel = useMemo(() => {
    if (lapSpliceLoading) {
      return 'calculando';
    }
    if (typeof computedLapSpliceLength === 'number') {
      return `${computedLapSpliceLength.toFixed(2)} m`;
    }
    return '—';
  }, [lapSpliceLoading, computedLapSpliceLength]);

  const handleLevelBlur = (event) => {
    const rawValue = event.target.value;
    if (rawValue === '') {
      return;
    }
    const parsed = Number(rawValue);
    if (Number.isNaN(parsed)) {
      return;
    }
    const formatted = Number(parsed.toFixed(2));
    setValue('element_level', formatted, { shouldValidate: true, shouldDirty: true });
  };

  const expandBarConfig = (config) => {
    if (!Array.isArray(config)) {
      return [];
    }
    const expanded = [];
    config.forEach((group) => {
      const qty = Number(group?.quantity);
      const diameter = group?.diameter;
      if (!Number.isFinite(qty) || qty <= 0 || !diameter) {
        return;
      }
      for (let index = 0; index < qty; index += 1) {
        expanded.push(diameter);
      }
    });
    return expanded;
  };

  const handleComputeDetailing = async () => {
    const values = watch();
    const beamData = extractBeamData(values);

    const result = await computeDetailing(beamData);
    if (result.success) {
      setDetailingResults(result.data);
      setShowDetailing(true);
    }
  };

  const syncDesignDetailing = async (designId) => {
    if (!designId) {
      return null;
    }
    try {
      const response = await apiClient.post(`/api/v1/tools/despiece/designs/${designId}/compute-detailing`);
      if (response.data?.success && response.data?.results) {
        setDetailingResults(response.data.results);
        setShowDetailing(true);
      }
      return response.data;
    } catch (error) {
      const backendMessage = error.response?.data?.detail;
      toast.error(backendMessage || 'No se pudo sincronizar el despiece con el plano.');
      return null;
    }
  };

  const onSubmit = async (values) => {
    setIsSubmitting(true);
    try {
      const {
        axis_supports,
        span_geometries,
        has_initial_cantilever,
        has_final_cantilever,
        stirrups_config,
        top_bars_config,
        bottom_bars_config,
        segment_reinforcements,
        element_level,
        beam_total_length_m,
        lap_splice_length_min_m: _legacyLapSpliceLength,
        lap_splice_location: _legacyLapSpliceLocation,
        ...rest
      } = values;

      const formattedLevel =
        typeof element_level === 'number' && Number.isFinite(element_level)
          ? Number(element_level.toFixed(2))
          : null;

      const axisNumbering = (axis_supports || [])
        .map((axis) => (axis?.label || '').trim())
        .filter((label) => label.length > 0)
        .join(' · ');

      const supportWidths = (axis_supports || []).map((axis) => {
        const width = Number(axis?.support_width_cm);
        if (!Number.isFinite(width)) {
          return 0;
        }
        return Number(width.toFixed(2));
      });

      const spanGeometryPayload = (span_geometries || []).map((span, index) => ({
        label: `Luz ${index + 1}`,
        clear_span_between_supports_m: formatDimensionValue(span.clear_span_between_supports_m),
        base_cm: formatDimensionValue(span.section_base_cm),
        height_cm: formatDimensionValue(span.section_height_cm),
      }));

      const validSectionChanges = spanGeometryPayload.filter(
        (entry) =>
          entry.base_cm !== null && entry.height_cm !== null && entry.clear_span_between_supports_m !== null
      );

      const hasCantilevers = Boolean(has_initial_cantilever || has_final_cantilever);
      const expandedTopBars = expandBarConfig(top_bars_config);
      const expandedBottomBars = expandBarConfig(bottom_bars_config);
      const normalizeRebarGroup = (quantity, diameter) => {
        const qtyValue = Number(quantity);
        if (!Number.isFinite(qtyValue) || !diameter) {
          return null;
        }
        return { quantity: qtyValue, diameter };
      };
      const segmentReinforcementsPayload = (segment_reinforcements || [])
        .map((entry) => {
          const spanIndexes = Array.isArray(entry?.span_indexes)
            ? entry.span_indexes
                .map((index) => Number(index))
                .filter((index) => Number.isFinite(index) && index >= 0)
            : [];
          return {
            span_indexes: spanIndexes,
            top_rebar: normalizeRebarGroup(entry.top_quantity, entry.top_diameter),
            bottom_rebar: normalizeRebarGroup(entry.bottom_quantity, entry.bottom_diameter),
          };
        })
        .filter((entry) => entry.span_indexes.length > 0 && (entry.top_rebar || entry.bottom_rebar));

      const payload = {
        ...rest,
        element_level: formattedLevel,
        has_cantilevers: hasCantilevers,
        beam_total_length_m: Number(beam_total_length_m) || 0,
        axis_numbering: axisNumbering || null,
        support_widths_cm: supportWidths,
        span_geometries: spanGeometryPayload,
        top_bars_qty: expandedTopBars.length,
        bottom_bars_qty: expandedBottomBars.length,
        top_bar_diameters: expandedTopBars,
        bottom_bar_diameters: expandedBottomBars,
        section_changes: validSectionChanges.length ? validSectionChanges : null,
        segment_reinforcements: segmentReinforcementsPayload.length ? segmentReinforcementsPayload : null,
        stirrups_config: stirrups_config.map((stirrup) => ({
          additional_branches: Number(stirrup.additional_branches),
          stirrup_type: stirrup.stirrup_type,
        })),
      };

      if (!getAccessToken() && !getRefreshToken()) {
        throw new Error('Tu sesión expiró, inicia sesión nuevamente.');
      }

      const response = await apiClient.post('/api/v1/tools/despiece/designs', payload);

      setLastDesign(response.data);
      toast.success('Despiece guardado correctamente.');

      await syncDesignDetailing(response.data?.id);
    } catch (error) {
      const backendMessage = error.response?.data?.detail;
      toast.error(backendMessage || error.message || 'No se pudo guardar el despiece.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderError = (fieldName) =>
    errors[fieldName] ? (
      <p className="text-rose-400 text-xs mt-1">{errors[fieldName]?.message}</p>
    ) : null;

  return (
    <div className="min-h-screen bg-[#050b16] text-slate-100 font-[Inter]">
      <header className="border-b border-slate-800 bg-[#0f172a] px-8 py-4 flex items-center justify-between">
        <div>
          <p className="text-[11px] tracking-[0.45em] uppercase text-slate-500">Despiece de vigas</p>
          <h1 className="text-2xl font-semibold tracking-wide">Panel técnico NSR-10</h1>
        </div>
        <div className="flex gap-3">
          <div className="flex bg-[#050b16] border border-slate-700 rounded-2xl p-1 text-[11px] font-bold uppercase tracking-[0.3em]">
            {energyOptions.map((option) => (
              <button
                type="button"
                key={option}
                onClick={() => setValue('energy_dissipation_class', option, { shouldDirty: true })}
                className={`px-3 py-1 rounded-xl transition-colors ${
                  energyClass === option ? 'bg-primary text-white' : 'text-slate-400'
                }`}
              >
                {option}
              </button>
            ))}
          </div>
          <div className="flex gap-1 bg-slate-900/40 border border-slate-700 rounded-2xl px-4 py-2">
            <span className="material-symbols-outlined text-lg">bolt</span>
            <span className="text-xs uppercase tracking-[0.25em]">Modo Sísmico</span>
          </div>
        </div>
      </header>

      <main className="grid grid-cols-1 xl:grid-cols-[1.35fr_0.85fr] gap-8 px-8 py-10">
        <section className="bg-[#0c1326] border border-slate-800/70 rounded-3xl p-8 shadow-[0_20px_80px_rgba(2,6,23,0.75)]">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
            <BlockIdentification
              register={register}
              renderError={renderError}
              elementLevelField={elementLevelField}
              handleLevelBlur={handleLevelBlur}
              energyOptions={energyOptions}
            />

            <BlockGeometrySupports
              register={register}
              renderError={renderError}
              axisSupportFields={axisSupportFields}
              spanGeometryFields={spanGeometryFields}
              errors={errors}
              spanOverview={spanOverview}
            />

            <BlockReinforcement
              register={register}
              control={control}
              errors={errors}
              renderError={renderError}
              selectedLength={selectedLength}
              setValue={setValue}
              lengthOptions={lengthOptions}
              hookOptions={hookOptions}
              diameterOptions={diameterOptions}
              topBarFields={topBarFields}
              appendTopBarGroup={appendTopBarGroup}
              removeTopBarGroup={removeTopBarGroup}
              bottomBarFields={bottomBarFields}
              appendBottomBarGroup={appendBottomBarGroup}
              removeBottomBarGroup={removeBottomBarGroup}
              totalTopBars={totalTopBars}
              totalBottomBars={totalBottomBars}
              topBarCharacteristics={topBarCharacteristics}
              bottomBarCharacteristics={bottomBarCharacteristics}
              topBarsGroupError={topBarsGroupError}
              bottomBarsGroupError={bottomBarsGroupError}
              segmentReinforcementFields={segmentReinforcementFields}
              appendSegmentReinforcement={appendSegmentReinforcement}
              removeSegmentReinforcement={removeSegmentReinforcement}
              segmentReinforcementsError={segmentReinforcementsError}
              spanOptions={spanOptions}
              stirrupFields={stirrupFields}
              appendStirrup={appendStirrup}
              removeStirrup={removeStirrup}
              stirrupTypeOptions={STIRRUP_TYPE_OPTIONS}
              lapSpliceLength={computedLapSpliceLength}
              isLapSpliceLoading={lapSpliceLoading}
              concreteStrength={watchConcreteStrength}
              onComputeDetailing={handleComputeDetailing}
              isDetailingComputing={isDetailingComputing}
              detailingError={detailingError}
              nsrWarnings={nsrWarnings}
            />

            <div className="flex flex-col sm:flex-row gap-4">
              <button
                type="button"
                onClick={handleComputeDetailing}
                disabled={isDetailingComputing}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-3 rounded-2xl text-sm font-bold uppercase tracking-[0.3em] transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDetailingComputing ? (
                  <>
                    <span className="material-symbols-outlined animate-spin mr-2">refresh</span>
                    Calculando...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined mr-2">calculate</span>
                    Calcular Despiece NSR-10
                  </>
                )}
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 bg-primary/90 hover:bg-primary text-white py-3 rounded-2xl text-sm font-bold uppercase tracking-[0.3em] transition disabled:opacity-50"
              >
                {isSubmitting ? 'Guardando…' : 'Guardar despiece'}
              </button>
              <button
                type="button"
                onClick={() => reset(defaultValues)}
                className="px-6 py-3 rounded-2xl border border-slate-700 text-sm font-bold uppercase tracking-[0.3em]"
              >
                Restaurar
              </button>
            </div>
          </form>
        </section>

        <aside className="space-y-6">
          <DespieceExportPanel
            designId={lastDesign?.id}
            projectName={activeProjectName}
            beamLabel={activeBeamLabel}
            lastSavedAt={lastDesign?.updated_at || lastDesign?.created_at}
          />

          <div className="bg-[#050b16] border border-slate-800 rounded-3xl p-6 space-y-4 shadow-[0_20px_60px_rgba(2,6,23,0.65)]">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-[0.35em] text-slate-400">Especificación estribos</h2>
              <span className="text-xs text-slate-400">Φ {DEFAULT_STIRRUP_DIAMETER} · {DEFAULT_STIRRUP_HOOK_TYPE}°</span>
            </div>
            {stirrupBaseSpecs.length ? (
              <div className="space-y-3">
                {stirrupBaseSpecs.map((spec) => (
                  <div key={spec.label} className="rounded-2xl border border-slate-800 bg-[#070d1c] p-3 text-xs">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="font-semibold text-slate-200 tracking-[0.3em]">{spec.label}</span>
                      <span>d = {spec.effectiveDepthCm.toFixed(1)} cm</span>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Dimensiones</p>
                        <p className="text-slate-100 font-semibold">{spec.stirrupWidthCm.toFixed(1)} × {spec.stirrupHeightCm.toFixed(1)} cm</p>
                        {typeof spec.stirrupTotalLengthCm === 'number' ? (
                          <p className="mt-1 text-[10px] uppercase tracking-[0.2em] text-slate-500">
                            Longitud:
                            <span className="ml-1 text-slate-100 font-semibold">
                              {spec.stirrupTotalLengthCm.toFixed(1)} cm
                            </span>
                          </p>
                        ) : null}
                      </div>
                      <div>
                        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Espaciados</p>
                        <p className="text-slate-100 font-semibold">d/4 = {spec.spacingConfinedCm.toFixed(1)} cm</p>
                        <p className="text-slate-400">d/2 = {spec.spacingNonConfinedCm.toFixed(1)} cm</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">Añade al menos una luz para estimar la geometría del estribo.</p>
            )}

            <div className="pt-4 border-t border-slate-800">
              <p className="text-[11px] uppercase tracking-[0.35em] text-slate-400 mb-2">Distribución NSR-10</p>
              {detailingStirrupsSummary ? (
                <div className="space-y-3 text-xs">
                  <p className="text-slate-300">
                    Ramas adicionales declaradas: {detailingStirrupsSummary.additional_branches_total || 0}
                  </p>
                  {typeof stirrupEstimatedTotal === 'number' ? (
                    <p className="text-slate-300">
                      Total estimado de estribos: <span className="text-slate-100 font-semibold">{stirrupEstimatedTotal}</span> uds
                    </p>
                  ) : null}
                  {(() => {
                    const mergedSegments = Object.entries(stirrupSegmentsByZone || {})
                      .flatMap(([zoneKey, segments = []]) =>
                        segments.map((segment) => ({
                          ...segment,
                          zoneKey,
                        }))
                      )
                      .sort((a, b) => a.start_m - b.start_m);

                    if (!mergedSegments.length) {
                      return <p className="text-slate-500">Sin segmentos definidos.</p>;
                    }

                    return (
                      <div className="space-y-1">
                        {mergedSegments.map((segment, idx) => {
                          const spacingCm = (segment.spacing_m * 100).toFixed(1);
                          const start = segment.start_m.toFixed(2);
                          const end = segment.end_m.toFixed(2);
                          const count = segment.estimated_count ?? '—';
                          const isConfined = segment.zoneKey === 'confined';
                          const zoneLabel = isConfined ? 'ZC (d/4)' : 'ZNC (d/2)';
                          const zoneBadgeClass = isConfined ? 'bg-primary/20 text-primary' : 'bg-emerald-500/10 text-emerald-300';
                          return (
                            <div
                              key={`${segment.zoneKey}-${start}-${idx}`}
                              className="grid grid-cols-[auto_auto_auto_auto] gap-3 items-center bg-[#090f1e] border border-slate-800 rounded-xl px-3 py-1 text-slate-200"
                            >
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${zoneBadgeClass}`}>
                                {zoneLabel}
                              </span>
                              <span className="text-primary text-[11px] font-semibold">{spacingCm} cm</span>
                              <span>{start} – {end} m</span>
                              <span className="text-right text-slate-400">{count} uds</span>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>
              ) : (
                <p className="text-xs text-slate-500">Genera el despiece para visualizar la distribución normativa.</p>
              )}
            </div>
          </div>

          <div className="bg-[#0c1326] border border-slate-800 rounded-3xl p-6 space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-[0.4em] text-slate-400">Último registro</h2>
            {lastDesign ? (
              <div className="text-sm space-y-1">
                <p className="text-slate-300 font-semibold">{lastDesign.title}</p>
                <p className="text-slate-400">{lastDesign.description}</p>
                {lastDesign.despiece_viga && (
                  <p className="text-slate-400">
                    {lastDesign.despiece_viga.top_bars_qty} sup. / {lastDesign.despiece_viga.bottom_bars_qty} inf. · ganchos {lastDesign.despiece_viga.hook_type}°
                  </p>
                )}
                {lastDesign.despiece_viga && (
                  <p className="text-slate-500 text-xs">
                    Φ sup: {(lastDesign.despiece_viga.top_bar_diameters || []).join(', ') || '—'} · Φ inf: {(lastDesign.despiece_viga.bottom_bar_diameters || []).join(', ') || '—'}
                  </p>
                )}
                <p className="text-slate-500 text-xs">
                  Guardado el {new Date(lastDesign.created_at).toLocaleString('es-CO')}
                </p>
              </div>
            ) : (
              <p className="text-slate-500 text-sm">Aún no has sincronizado este despiece.</p>
            )}
          </div>

          {showDetailing && (
            <div className="bg-[#0c1326] border border-slate-800 rounded-3xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-[0.4em] text-slate-400">
                  Despiece Automático NSR-10
                </h2>
                <button
                  type="button"
                  onClick={() => setShowDetailing(false)}
                  className="text-xs text-slate-500 hover:text-slate-300"
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>

              {detailingError && (
                <div className="bg-rose-900/20 border border-rose-700/50 rounded-xl p-4">
                  <p className="text-rose-300 text-sm">{detailingError}</p>
                </div>
              )}

              <BeamDetailingView detailingResults={detailingResults} beamData={extractBeamData(watch())} />
            </div>
          )}

          <div className="bg-gradient-to-br from-primary/40 via-indigo-500/20 to-slate-900 rounded-3xl border border-primary/30 p-6 text-sm">
            <p className="uppercase tracking-[0.4em] text-[11px] text-slate-200 mb-3">Checklist normativo</p>
            <ul className="space-y-2">
              <li className="flex items-center gap-2 text-slate-200">
                <span className="material-symbols-outlined text-base text-emerald-300">check_circle</span>
                Traslapos ≥ {lapSpliceChecklistLabel}
              </li>
              <li className="flex items-center gap-2 text-slate-200">
                <span className="material-symbols-outlined text-base text-emerald-300">check_circle</span>
                Energía {energyClass}
              </li>
              <li className="flex items-center gap-2 text-slate-200">
                <span className="material-symbols-outlined text-base text-emerald-300">check_circle</span>
                fc = {watch('concrete_strength')}
              </li>
            </ul>
          </div>
        </aside>
      </main>

      <style>{`
        .label {
          display: block;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.3em;
          color: #94a3b8;
          margin-bottom: 0.5rem;
        }
        .input {
          width: 100%;
          background: #050b16;
          border: 1px solid rgba(148, 163, 184, 0.35);
          border-radius: 1.25rem;
          padding: 0.65rem 1rem;
          font-size: 0.9rem;
          color: #f8fafc;
          transition: box-shadow 0.2s ease, border-color 0.2s ease;
        }
        .input-compact {
          padding: 0.25rem 0.65rem;
          font-size: 0.8rem;
          border-radius: 0.9rem;
          height: 2.1rem;
          line-height: 1.1;
        }
        .input-short {
          max-width: 11rem;
        }
        .input:focus {
          outline: none;
          border-color: rgba(99, 102, 241, 0.8);
          box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25);
        }
        .input::placeholder {
          color: rgba(148, 163, 184, 0.6);
        }
        .no-spin::-webkit-inner-spin-button,
        .no-spin::-webkit-outer-spin-button {
          -webkit-appearance: none;
          margin: 0;
        }
        .no-spin {
          -moz-appearance: textfield;
        }
        .material-symbols-outlined {
          font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 24;
        }
      `}</style>
    </div>
  );
};

export default DesignStudio;
