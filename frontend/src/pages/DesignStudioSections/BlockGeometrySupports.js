import React from 'react';

const BlockGeometrySupports = ({ register, renderError, axisSupportFields, spanGeometryFields, errors, spanOverview }) => (
  <div className="space-y-6 bg-[#040916]/60 border border-slate-900/80 rounded-3xl p-6 shadow-[0_16px_60px_rgba(2,6,23,0.55)]">
    <header className="flex items-center justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Bloque 02</p>
        <h2 className="text-lg font-semibold">Geometría y apoyos</h2>
      </div>
      <span className="text-xs text-slate-400">Tramos · ejes · secciones</span>
    </header>

    <div>
      <label className="label">Número de luces</label>
      <input
        type="number"
        min={1}
        step={1}
        className="input input-compact input-short"
        {...register('span_count', { valueAsNumber: true })}
      />
      {renderError('span_count')}
      <p className="text-xs text-slate-400 mt-1 italic">* Incluye tramos en Voladizo inicial o final</p>
    </div>

    <div>
      <label className="label">Voladizos</label>
      <div className="grid sm:grid-cols-2 gap-4">
        <label className="flex items-center gap-3 bg-slate-900/50 border border-slate-800 rounded-2xl px-4 py-3 text-sm">
          <input type="checkbox" className="accent-primary" {...register('has_initial_cantilever')} />
          Voladizo inicial
        </label>
        <label className="flex items-center gap-3 bg-slate-900/50 border border-slate-800 rounded-2xl px-4 py-3 text-sm">
          <input type="checkbox" className="accent-primary" {...register('has_final_cantilever')} />
          Voladizo final
        </label>
      </div>
    </div>

    <div>
      <label className="label">Ejes y Ancho de Apoyos</label>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {axisSupportFields.length === 0 ? (
          <p className="text-xs text-slate-500 col-span-full">Ajusta el número de luces para definir los ejes.</p>
        ) : (
          axisSupportFields.map((field, index) => (
            <div key={field.id} className="border border-slate-800 rounded-2xl p-3 space-y-2 bg-slate-900/30">
              <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Eje {index + 1}</p>
              <div className="flex gap-2 items-end">
                <div className="flex-1">
                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-1">Nombre</p>
                  <input
                    className="input input-compact"
                    placeholder={`EJE ${index + 1}`}
                    {...register(`axis_supports.${index}.label`)}
                  />
                </div>
                <div className="w-24">
                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-1">Ancho (cm)</p>
                  <input
                    type="number"
                    step={5}
                    min={0}
                    className="input input-compact text-sm"
                    placeholder="0"
                    {...register(`axis_supports.${index}.support_width_cm`, { valueAsNumber: true })}
                  />
                </div>
              </div>
              <p className="text-[10px] text-slate-500">0 cuando exista voladizo.</p>
            </div>
          ))
        )}
      </div>
    </div>

    <div className="rounded-2xl border border-slate-800/70 bg-[#050b16]/30 p-5 space-y-4">
      <p className="text-[11px] uppercase tracking-[0.4em] text-slate-500">Luces y secciones</p>
      {spanGeometryFields.length === 0 ? (
        <p className="text-xs text-slate-500">Ajusta el número de luces para generar las configuraciones.</p>
      ) : (
        <div className="space-y-4">
          {spanGeometryFields.map((field, index) => (
            <div key={field.id} className="border border-slate-800 rounded-2xl p-4 bg-slate-900/30 space-y-4">
              <div className="grid lg:grid-cols-[160px_minmax(0,1fr)] gap-4 items-start">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-1">Luz {index + 1}</p>
                  <label className="label">Luz libre (m)</label>
                  <input
                    type="number"
                    step="0.01"
                    lang="en"
                    inputMode="decimal"
                    className="input input-compact input-short"
                    {...register(`span_geometries.${index}.clear_span_between_supports_m`, { valueAsNumber: true })}
                  />
                  {errors.span_geometries?.[index]?.clear_span_between_supports_m && (
                    <p className="text-rose-400 text-xs mt-1">
                      {errors.span_geometries[index].clear_span_between_supports_m.message}
                    </p>
                  )}
                </div>
                <div>
                  <label className="label">Sección</label>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div>
                      <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500 mb-2">Base (cm)</p>
                      <input
                        type="number"
                        step={5}
                        min={5}
                        className="input"
                        placeholder="30"
                        {...register(`span_geometries.${index}.section_base_cm`, { valueAsNumber: true })}
                      />
                      {errors.span_geometries?.[index]?.section_base_cm && (
                        <p className="text-rose-400 text-xs mt-1">
                          {errors.span_geometries[index].section_base_cm.message}
                        </p>
                      )}
                    </div>
                    <div>
                      <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500 mb-2">Altura (cm)</p>
                      <input
                        type="number"
                        step={5}
                        min={5}
                        className="input"
                        placeholder="45"
                        {...register(`span_geometries.${index}.section_height_cm`, { valueAsNumber: true })}
                      />
                      {errors.span_geometries?.[index]?.section_height_cm && (
                        <p className="text-rose-400 text-xs mt-1">
                          {errors.span_geometries[index].section_height_cm.message}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>

    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-2">Luces</p>
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">straighten</span>
          <div>
            <p className="text-2xl font-semibold">{spanOverview.totalSpans}</p>
            <p className="text-xs text-slate-400">Tramos principales</p>
          </div>
        </div>
      </div>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-2">Voladizos</p>
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-amber-300">north_east</span>
          <div>
            <p className="text-base font-semibold">{spanOverview.cantileverLabel}</p>
            <p className="text-xs text-slate-400">Configuración activa</p>
          </div>
        </div>
      </div>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-4">
        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500 mb-2">Longitud total</p>
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-emerald-300">deployed_code</span>
          <div>
            <p className="text-2xl font-semibold">{spanOverview.totalLengthLabel} m</p>
            <p className="text-xs text-slate-400">Luces + apoyos</p>
          </div>
        </div>
      </div>
    </div>
  </div>
);

export default BlockGeometrySupports;
