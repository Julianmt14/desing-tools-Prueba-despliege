import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useForm, useFieldArray } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import BlockIdentification from './DesignStudioSections/BlockIdentification';
import BlockGeometrySupports from './DesignStudioSections/BlockGeometrySupports';
import BlockReinforcement from './DesignStudioSections/BlockReinforcement';
import {
  MAX_BAR_LENGTH_OPTIONS,
  getEnergyOptions,
  getHookOptionsForClass,
  getDiameterOptions,
  validateNSR10,
} from '../utils/nsr10Constants';
import { useBeamDetailing, extractBeamData } from '../hooks/useBeamDetailing';
import BeamDetailingView from './DesignStudioSections/BeamDetailingView';


const energyOptions = getEnergyOptions();
const lengthOptions = MAX_BAR_LENGTH_OPTIONS;
const diameterOptions = getDiameterOptions();
const DEFAULT_ENERGY_CLASS = 'DES';
const defaultHookOptions = getHookOptionsForClass(DEFAULT_ENERGY_CLASS);
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
  zone: z.string().min(1, 'Requerido'),
  spacing_m: z.coerce.number().positive('Ingrese un espaciamiento válido'),
  quantity: z.coerce.number().int().positive('Cantidad inválida'),
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
  lap_splice_length_min_m: z.coerce.number().positive('Longitud inválida'),
  lap_splice_location: z.string().min(1, 'Describe la ubicación'),
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
  notes: z.string().optional(),
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
  lap_splice_length_min_m: 0.75,
  lap_splice_location: 'Traslapo centrado a 1.50 m del apoyo A',
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
    { zone: 'Confinada', spacing_m: 0.07, quantity: 18 },
    { zone: 'Central', spacing_m: 0.15, quantity: 12 },
  ],
  energy_dissipation_class: DEFAULT_ENERGY_CLASS,
  concrete_strength: '21 MPa (3000 psi)',
  reinforcement: '420 MPa (Grado 60)',
  notes: 'Detalle conforme a NSR-10 Título C.\nConsiderar recubrimientos adicionales por exposición costa.',
};

defaultValues.beam_total_length_m = calculateBeamTotalLength(defaultValues.span_geometries, defaultValues.axis_supports);

const DesignStudio = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastDesign, setLastDesign] = useState(null);
  const [hookOptions, setHookOptions] = useState(() => defaultHookOptions);
  const [showDetailing, setShowDetailing] = useState(false);
  const [detailingResults, setDetailingResults] = useState(null);

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
  const beamTotalLength = useMemo(
    () => calculateBeamTotalLength(watchSpanGeometries, watchAxisSupports),
    [watchSpanGeometries, watchAxisSupports]
  );
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

  const preview = useMemo(() => {
    const totalLength =
      watchSpanGeometries?.reduce((sum, span) => sum + Number(span.clear_span_between_supports_m || 0), 0) || 0;
    const stirrupCount = watchStirrups?.reduce((sum, zone) => sum + Number(zone.quantity || 0), 0) || 0;
    return {
      totalLength: totalLength.toFixed(2),
      stirrupCount,
    };
  }, [watchSpanGeometries, watchStirrups]);

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

  const onSubmit = async (values) => {
    setIsSubmitting(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Tu sesión expiró, inicia sesión nuevamente.');
      }

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
        stirrups_config: stirrups_config.map((zone) => ({
          zone: zone.zone,
          spacing_m: Number(zone.spacing_m),
          quantity: Number(zone.quantity),
        })),
      };

      const response = await axios.post('/api/v1/tools/despiece/designs', payload, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setLastDesign(response.data);
      toast.success('Despiece guardado correctamente.');
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
              onComputeDetailing={handleComputeDetailing}
              isDetailingComputing={isDetailingComputing}
              detailingError={detailingError}
              nsrWarnings={nsrWarnings}
            />

            <div>
              <label className="label">Notas</label>
              <textarea className="input h-24" {...register('notes')} placeholder="Condiciones, recubrimientos, observaciones" />
            </div>

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
          <div className="bg-[#050b16] border border-slate-800 rounded-3xl p-6 shadow-[0_20px_60px_rgba(2,6,23,0.65)]">
            <p className="text-[11px] uppercase tracking-[0.5em] text-slate-500 mb-5">Vista previa</p>
            <div className="h-44 rounded-2xl border border-primary/30 relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-950">
              <div className="absolute inset-4 border border-dashed border-primary/30 rounded-2xl" />
              <div className="absolute top-4 left-6 bg-primary/20 text-primary text-[11px] px-3 py-1 rounded-full font-mono">
                Luz total: {preview.totalLength} m
              </div>
              <div className="absolute bottom-4 right-6 bg-emerald-500/20 text-emerald-300 text-[11px] px-3 py-1 rounded-full font-mono">
                Estribos: {preview.stirrupCount}
              </div>
              <div className="absolute inset-0 flex items-center justify-center gap-2">
                {watchSpanGeometries?.map((span, index) => (
                  <div
                    key={`${span.label || 'luz'}-${index}`}
                    className="h-12 border border-primary/50 rounded-full px-4 flex flex-col justify-center text-[10px] text-slate-200"
                  >
                    <span className="font-mono text-primary tracking-[0.3em]">L{index + 1}</span>
                    <span>L={span.clear_span_between_supports_m || '--'} m · {span.section_base_cm || '--'}x{span.section_height_cm || '--'} cm</span>
                  </div>
                ))}
              </div>
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
                Traslapos ≥ {watch('lap_splice_length_min_m')} m
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
