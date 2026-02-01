const DEFAULT_STIRRUP_DIAMETER = '#3';
const DEFAULT_STIRRUP_HOOK_TYPE = '135';
const INNER_CLEARANCE_CM = 2;

const STIRRUP_HOOK_LENGTHS_CM = {
  '#2': { '135': 7.5 },
  '#3': { '135': 9.5 },
  '#4': { '135': 12.7 },
  '#5': { '135': 15.9 },
  '#6': { '135': 19.1 },
  '#7': { '135': 22.2 },
  '#8': { '135': 25.4 },
};

const sanitizeNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export const calculateEffectiveDepth = (sectionHeightCm, coverCm) => {
  const height = Math.max(sanitizeNumber(sectionHeightCm), 0);
  const cover = Math.max(sanitizeNumber(coverCm), 0);
  const dCm = Math.max(height - cover - INNER_CLEARANCE_CM, 0);
  return dCm / 100;
};

export const calculateSpacingForZone = (effectiveDepthM, zoneType) => {
  const factor = zoneType === 'confined' ? 0.25 : 0.5;
  return Math.max(0, effectiveDepthM * factor);
};

export const getDefaultStirrupSpec = (sectionHeightCm, coverCm) => {
  const d = calculateEffectiveDepth(sectionHeightCm, coverCm);
  return {
    diameter: DEFAULT_STIRRUP_DIAMETER,
    hookType: DEFAULT_STIRRUP_HOOK_TYPE,
    spacingConfinedM: calculateSpacingForZone(d, 'confined'),
    spacingNonConfinedM: calculateSpacingForZone(d, 'non_confined'),
  };
};

const mergeSegments = (segments) => {
  const sanitized = (segments || [])
    .map(([start, end]) => [Math.min(start, end), Math.max(start, end)])
    .filter(([start, end]) => Number.isFinite(start) && Number.isFinite(end) && end > start)
    .sort((a, b) => a[0] - b[0]);

  if (!sanitized.length) {
    return [];
  }

  const merged = [];
  let [currentStart, currentEnd] = sanitized[0];

  for (const [start, end] of sanitized.slice(1)) {
    if (start <= currentEnd) {
      currentEnd = Math.max(currentEnd, end);
      continue;
    }
    merged.push([currentStart, currentEnd]);
    currentStart = start;
    currentEnd = end;
  }

  merged.push([currentStart, currentEnd]);
  return merged;
};

export const deriveConfinedSegments = (prohibitedZones, lapSplices) => {
  const segments = [];
  (prohibitedZones || []).forEach((zone) => {
    if (!zone) return;
    if (zone.support_index == null && zone.supportIndex == null) return;
    const description = (zone.description || '').toLowerCase();
    if (description.includes('dentro del apoyo')) return;
    segments.push([zone.start_m ?? zone.start, zone.end_m ?? zone.end]);
  });

  (lapSplices || []).forEach((splice) => {
    if (!splice) return;
    const start = splice.start_m ?? splice.start;
    const end = splice.end_m ?? splice.end;
    if (Number.isFinite(start) && Number.isFinite(end) && end > start) {
      segments.push([start, end]);
    }
  });

  return mergeSegments(segments);
};

export const deriveUnconfinedSegments = (totalLength, confinedSegments) => {
  const length = Math.max(sanitizeNumber(totalLength), 0);
  if (length === 0) {
    return [];
  }
  const mergedConfined = mergeSegments(confinedSegments || []);
  const segments = [];
  let cursor = 0;
  mergedConfined.forEach(([start, end]) => {
    if (start > cursor) {
      segments.push([cursor, start]);
    }
    cursor = Math.max(cursor, end);
  });
  if (cursor < length) {
    segments.push([cursor, length]);
  }
  return segments.filter(([start, end]) => end > start);
};

export const extractSpliceSegments = (rebarDetails) => {
  const segments = [];
  (rebarDetails || []).forEach((bar) => {
    const splices = bar?.splices;
    if (!Array.isArray(splices)) return;
    splices.forEach((splice) => {
      if (!splice) return;
      const start = splice.start_m ?? splice.start;
      const end = splice.end_m ?? splice.end;
      if (Number.isFinite(start) && Number.isFinite(end) && end > start) {
        segments.push([start, end]);
      }
    });
  });
  return mergeSegments(segments);
};

export const getStirrupHookLengthCm = (barMark = DEFAULT_STIRRUP_DIAMETER, hookType = DEFAULT_STIRRUP_HOOK_TYPE) => {
  if (!barMark) {
    return null;
  }
  const normalizedMark = String(barMark).startsWith('#') ? String(barMark) : `#${barMark}`;
  const normalizedHook = String(hookType || '').trim();
  const hookValue = STIRRUP_HOOK_LENGTHS_CM[normalizedMark]?.[normalizedHook];
  return Number.isFinite(hookValue) ? hookValue : null;
};

export const estimateStirrupTotalLengthCm = (
  widthCm,
  heightCm,
  { barMark = DEFAULT_STIRRUP_DIAMETER, hookType = DEFAULT_STIRRUP_HOOK_TYPE } = {}
) => {
  const width = Math.max(sanitizeNumber(widthCm), 0);
  const height = Math.max(sanitizeNumber(heightCm), 0);
  const perimeterCm = 2 * (width + height);
  const hookLengthCm = getStirrupHookLengthCm(barMark, hookType);
  const totalLengthCm = perimeterCm + (hookLengthCm ? 2 * hookLengthCm : 0);
  return { totalLengthCm, hookLengthCm, perimeterCm };
};

export {
  DEFAULT_STIRRUP_DIAMETER,
  DEFAULT_STIRRUP_HOOK_TYPE,
  mergeSegments,
};
