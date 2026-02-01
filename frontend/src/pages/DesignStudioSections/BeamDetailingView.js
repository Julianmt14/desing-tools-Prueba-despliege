import React from 'react';

const BeamDetailingView = ({ detailingResults, beamData }) => {
  if (!detailingResults) {
    return (
      <div className="text-center py-8 text-slate-500">
        <span className="material-symbols-outlined text-4xl mb-2">engineering</span>
        <p>Ejecuta el cálculo para ver el despiece</p>
      </div>
    );
  }

  const { 
    top_bars = [], 
    bottom_bars = [], 
    prohibited_zones = [], 
    material_list = [], 
    warnings = [],
    validation_passed,
    continuous_bars
  } = detailingResults;

  const allBars = [...top_bars, ...bottom_bars];

  return (
    <div className="space-y-6">
      {/* Header con estado de validación */}
      <div className={`p-4 rounded-2xl ${validation_passed ? 'bg-emerald-900/20 border border-emerald-700' : 'bg-amber-900/20 border border-amber-700'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`material-symbols-outlined ${validation_passed ? 'text-emerald-400' : 'text-amber-400'}`}>
              {validation_passed ? 'check_circle' : 'warning'}
            </span>
            <div>
              <h3 className="font-semibold">
                Despiece NSR-10 {validation_passed ? '✓' : '⚠️'}
              </h3>
              <p className="text-sm text-slate-400">
                {validation_passed ? 'Cumple con normativa' : 'Revisar advertencias'}
              </p>
            </div>
          </div>
          <div className="text-xs text-slate-400">
            {allBars.length} barras · {material_list.length} diámetros
          </div>
        </div>
      </div>

      {/* Advertencias */}
      {warnings.length > 0 && (
        <div className="bg-amber-900/20 border border-amber-700/50 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-amber-400">warning</span>
            <h4 className="text-sm font-semibold text-amber-300">Advertencias NSR-10</h4>
          </div>
          <ul className="space-y-2">
            {warnings.map((warning, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-amber-200">
                <span className="material-symbols-outlined text-xs mt-0.5">arrow_right</span>
                {warning}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Zonas prohibidas */}
      {prohibited_zones.length > 0 && (
        <div className="bg-slate-900/50 border border-slate-700 rounded-2xl p-4">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">Zonas prohibidas para empalmes</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {prohibited_zones.map((zone, idx) => (
              <div key={idx} className="bg-slate-800/30 p-3 rounded-xl">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-rose-300 font-semibold">Zona {idx + 1}</span>
                  <span className="text-xs text-slate-400">{zone.start_m.toFixed(2)} - {zone.end_m.toFixed(2)} m</span>
                </div>
                <p className="text-xs text-slate-400">{zone.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Barras continuas */}
      {continuous_bars && (
        <div className="bg-slate-900/50 border border-slate-700 rounded-2xl p-4">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">Barras continuas obligatorias</h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-primary/10 p-3 rounded-xl">
              <p className="text-xs text-slate-400 mb-1">Superiores</p>
              <div className="flex flex-wrap gap-2">
                {continuous_bars.top?.diameters?.map((diam, idx) => (
                  <span key={idx} className="px-3 py-1 bg-primary/20 text-primary rounded-full text-sm">
                    {continuous_bars.top.count_per_diameter[diam] || 0}x{diam}
                  </span>
                ))}
                {(!continuous_bars.top?.diameters || continuous_bars.top.diameters.length === 0) && (
                  <span className="text-slate-500 text-sm">No definidas</span>
                )}
              </div>
            </div>
            <div className="bg-emerald-900/20 p-3 rounded-xl">
              <p className="text-xs text-slate-400 mb-1">Inferiores</p>
              <div className="flex flex-wrap gap-2">
                {continuous_bars.bottom?.diameters?.map((diam, idx) => (
                  <span key={idx} className="px-3 py-1 bg-emerald-500/20 text-emerald-300 rounded-full text-sm">
                    {continuous_bars.bottom.count_per_diameter[diam] || 0}x{diam}
                  </span>
                ))}
                {(!continuous_bars.bottom?.diameters || continuous_bars.bottom.diameters.length === 0) && (
                  <span className="text-slate-500 text-sm">No definidas</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Vista gráfica simplificada */}
      <div className="bg-slate-900/30 border border-slate-700 rounded-2xl p-4">
        <h4 className="text-sm font-semibold text-slate-300 mb-3">Distribución de barras</h4>
        <div className="relative h-24 bg-slate-950 rounded-xl overflow-hidden">
          {/* Eje de la viga */}
          <div className="absolute top-1/2 left-0 right-0 h-px bg-slate-700 transform -translate-y-1/2" />
          
          {/* Barras superiores */}
          <div className="absolute top-4 left-0 right-0 h-3">
            {top_bars.map((bar, idx) => (
              <div
                key={`top-${idx}`}
                className={`absolute h-3 rounded-full ${
                  bar.type === 'continuous' 
                    ? 'bg-primary/80' 
                    : bar.type === 'support'
                    ? 'bg-amber-500/80'
                    : 'bg-slate-600/80'
                }`}
                style={{
                  left: `${(bar.start_m / beamData?.beam_total_length_m || 1) * 100}%`,
                  width: `${Math.max(2, ((bar.end_m - bar.start_m) / beamData?.beam_total_length_m || 1) * 100)}%`,
                  opacity: 0.8
                }}
                title={`${bar.id}: ${bar.length_m.toFixed(2)}m`}
              />
            ))}
          </div>
          
          {/* Barras inferiores */}
          <div className="absolute bottom-4 left-0 right-0 h-3">
            {bottom_bars.map((bar, idx) => (
              <div
                key={`bottom-${idx}`}
                className={`absolute h-3 rounded-full ${
                  bar.type === 'continuous' 
                    ? 'bg-emerald-500/80' 
                    : bar.type === 'support_anchored'
                    ? 'bg-cyan-500/80'
                    : 'bg-slate-500/80'
                }`}
                style={{
                  left: `${(bar.start_m / beamData?.beam_total_length_m || 1) * 100}%`,
                  width: `${Math.max(2, ((bar.end_m - bar.start_m) / beamData?.beam_total_length_m || 1) * 100)}%`,
                  opacity: 0.8
                }}
                title={`${bar.id}: ${bar.length_m.toFixed(2)}m`}
              />
            ))}
          </div>
          
          {/* Zonas prohibidas */}
          {prohibited_zones.map((zone, idx) => (
            <div
              key={`zone-${idx}`}
              className="absolute top-0 bottom-0 bg-rose-500/10 border-l border-r border-rose-500/30"
              style={{
                left: `${(zone.start_m / beamData?.beam_total_length_m || 1) * 100}%`,
                width: `${((zone.end_m - zone.start_m) / beamData?.beam_total_length_m || 1) * 100}%`
              }}
            />
          ))}
          
          {/* Escala */}
          <div className="absolute bottom-1 left-2 text-[10px] text-slate-500">
            0 m
          </div>
          <div className="absolute bottom-1 right-2 text-[10px] text-slate-500">
            {(beamData?.beam_total_length_m || 0).toFixed(1)} m
          </div>
        </div>
        
        {/* Leyenda */}
        <div className="flex flex-wrap gap-3 mt-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-primary/80" />
            <span className="text-xs text-slate-400">Continuas sup.</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
            <span className="text-xs text-slate-400">Continuas inf.</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500/80" />
            <span className="text-xs text-slate-400">Apoyo</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-rose-500/20 border border-rose-500/30" />
            <span className="text-xs text-slate-400">No empalmar</span>
          </div>
        </div>
      </div>

      {/* Tabla de barras */}
      <div className="bg-slate-900/30 border border-slate-700 rounded-2xl p-4">
        <h4 className="text-sm font-semibold text-slate-300 mb-3">Detalle de barras</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left py-2 px-2 text-slate-400">ID</th>
                <th className="text-left py-2 px-2 text-slate-400">Φ</th>
                <th className="text-left py-2 px-2 text-slate-400">Pos.</th>
                <th className="text-left py-2 px-2 text-slate-400">Tipo</th>
                <th className="text-left py-2 px-2 text-slate-400">L (m)</th>
                <th className="text-left py-2 px-2 text-slate-400">Inicio</th>
                <th className="text-left py-2 px-2 text-slate-400">Fin</th>
                <th className="text-left py-2 px-2 text-slate-400">Cant.</th>
              </tr>
            </thead>
            <tbody>
              {allBars.map((bar, idx) => (
                <tr key={idx} className="border-b border-slate-800/30 hover:bg-slate-800/20">
                  <td className="py-2 px-2 font-mono text-xs">{bar.id}</td>
                  <td className="py-2 px-2">
                    <span className="px-2 py-1 bg-slate-700/50 rounded text-xs">
                      {bar.diameter}
                    </span>
                  </td>
                  <td className="py-2 px-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      bar.position === 'top' 
                        ? 'bg-primary/20 text-primary' 
                        : 'bg-emerald-500/20 text-emerald-300'
                    }`}>
                      {bar.position === 'top' ? 'Sup' : 'Inf'}
                    </span>
                  </td>
                  <td className="py-2 px-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      bar.type === 'continuous' 
                        ? 'bg-slate-700 text-slate-300'
                        : 'bg-amber-900/30 text-amber-300'
                    }`}>
                      {bar.type === 'continuous' ? 'Continua' : 
                       bar.type === 'support' ? 'Apoyo' :
                       bar.type === 'support_anchored' ? 'Apoyo ancl.' :
                       'Regular'}
                    </span>
                  </td>
                  <td className="py-2 px-2 font-mono">{bar.length_m.toFixed(2)}</td>
                  <td className="py-2 px-2 text-slate-400">{bar.start_m.toFixed(2)} m</td>
                  <td className="py-2 px-2 text-slate-400">{bar.end_m.toFixed(2)} m</td>
                  <td className="py-2 px-2 font-semibold">{bar.quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Lista de materiales */}
      {material_list.length > 0 && (
        <div className="bg-slate-900/30 border border-slate-700 rounded-2xl p-4">
          <h4 className="text-sm font-semibold text-slate-300 mb-3">Lista de materiales</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {material_list.map((item, idx) => (
              <div key={idx} className="bg-slate-800/20 p-4 rounded-xl">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-semibold">{item.diameter}</span>
                      <span className="text-xs text-slate-400 bg-slate-700/50 px-2 py-1 rounded">
                        {item.pieces} {item.pieces === 1 ? 'pieza' : 'piezas'}
                      </span>
                    </div>
                    <p className="text-sm text-slate-400 mt-1">
                      Longitud total: <span className="font-semibold">{item.total_length_m.toFixed(1)} m</span>
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold">{item.weight_kg.toFixed(1)} kg</div>
                    <div className={`text-xs ${item.waste_percentage > 15 ? 'text-rose-400' : item.waste_percentage > 5 ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {item.waste_percentage.toFixed(1)}% desperdicio
                    </div>
                  </div>
                </div>
                
                {item.commercial_lengths && item.commercial_lengths.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-700/50">
                    <p className="text-xs text-slate-400 mb-2">Cortes comerciales:</p>
                    <div className="space-y-2">
                      {item.commercial_lengths.map((cut, cutIdx) => (
                        <div key={cutIdx} className="flex justify-between items-center text-xs">
                          <span className="text-slate-300">
                            {cut.num_bars} barras de {cut.commercial_length}m
                          </span>
                          <span className="text-slate-400">
                            {cut.efficiency.toFixed(1)}% eficiencia
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BeamDetailingView;