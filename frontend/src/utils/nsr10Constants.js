// Constantes NSR-10 para referencia
export const NSR10_CONSTANTS = {
  // Factores según clase de disipación
  ENERGY_DISSIPATION_FACTORS: {
    'DES': 1.3,  // Alta disipación
    'DMO': 1.0,  // Moderada
    'DMI': 1.0   // Mínima
  },
  
  // Longitudes de desarrollo mínimas (m) para f'c=21MPa, fy=420MPa
  DEVELOPMENT_LENGTHS: {
    '#2': 0.25,
    '#3': 0.30,
    '#4': 0.40,
    '#5': 0.50,
    '#6': 0.60,
    '#7': 0.70, '#8': 0.80, '#9': 0.90, '#10': 1.00,
    '#11': 1.10, '#14': 1.40, '#18': 1.80
  },
  
  // Factores de ajuste para diferentes f'c
  FC_ADJUSTMENT_FACTORS: {
    '21 MPa (3000 psi)': 1.0,
    '24 MPa (3500 psi)': 0.92,
    '28 MPa (4000 psi)': 0.85,
    '32 MPa (4600 psi)': 0.80
  },
  
  // Tipos de gancho permitidos por clase
  ALLOWED_HOOKS_BY_CLASS: {
    'DES': ['135', '180'],  // Solo 135° o 180° para alta disipación
    'DMO': ['90', '135', '180'],
    'DMI': ['90', '135', '180']
  },
  
  // Requisitos mínimos de barras continuas
  MIN_CONTINUOUS_BARS: {
    top: 2,
    bottom: 2
  },
  
  // Porcentaje mínimo de refuerzo positivo en apoyos
  MIN_POSITIVE_IN_SUPPORTS: 0.33,  // 1/3
  
  // Zonas prohibidas para empalmes (en términos de peralte efectivo)
  NO_SPLICE_ZONE_FACTOR: 2.0,  // 2d desde cara de apoyo
};

export const MAX_BAR_LENGTH_OPTIONS = ['6m', '9m', '12m'];

const BASE_HOOK_VALUES = ['90', '135', '180'];

export const getEnergyOptions = () => Object.keys(NSR10_CONSTANTS.ENERGY_DISSIPATION_FACTORS);

export const getConcreteStrengthOptions = () => Object.keys(NSR10_CONSTANTS.FC_ADJUSTMENT_FACTORS);

export const getDiameterOptions = () => Object.keys(NSR10_CONSTANTS.DEVELOPMENT_LENGTHS);

export const getHookOptionsForClass = (energyClass) => {
  const allowed = NSR10_CONSTANTS.ALLOWED_HOOKS_BY_CLASS[energyClass] || BASE_HOOK_VALUES;
  return allowed.map((value) => ({ label: `${value}°`, value }));
};

// Validaciones específicas NSR-10
export const validateNSR10 = (beamData) => {
  const warnings = [];
  const { energy_dissipation_class, hook_type } = beamData;
  
  // Validar tipo de gancho según clase
  const allowedHooks = NSR10_CONSTANTS.ALLOWED_HOOKS_BY_CLASS[energy_dissipation_class] || [];
  if (!allowedHooks.includes(hook_type)) {
    warnings.push(`Clase ${energy_dissipation_class}: Se recomiendan ganchos de ${allowedHooks.join('° o ')}°`);
  }
  
  return warnings;
};

// Calcular longitud de desarrollo ajustada
export const calculateAdjustedDevelopmentLength = (diameter, concreteStrength) => {
  const baseLength = NSR10_CONSTANTS.DEVELOPMENT_LENGTHS[diameter] || 0.6;
  const fcFactor = NSR10_CONSTANTS.FC_ADJUSTMENT_FACTORS[concreteStrength] || 1.0;
  
  return baseLength * fcFactor;
};