import React from 'react';

const BlockReinforcement = ({
  register,
  errors,
  renderError,
  selectedLength,
  setValue,
  lengthOptions,
  hookOptions,
  diameterOptions,
  topBarFields,
  appendTopBarGroup,
  removeTopBarGroup,
  bottomBarFields,
  appendBottomBarGroup,
  removeBottomBarGroup,
  totalTopBars,
  totalBottomBars,
  topBarsGroupError,
  bottomBarsGroupError,
  stirrupFields,
  appendStirrup,
  removeStirrup,
}) => (
  <div className="space-y-6 bg-[#030a18]/70 border border-slate-900 rounded-3xl p-6 shadow-[0_18px_70px_rgba(2,6,23,0.6)]">
    <header className="flex items-center justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Bloque 03</p>
        <h2 className="text-lg font-semibold">Armaduras longitudinales y transversales</h2>
      </div>
      <span className="text-xs text-slate-400">Barras · Φ · L<sub>máx</sub> · traslapos</span>
    </header>

    <div className="bg-[#0b172f] border border-slate-800 rounded-3xl p-5 space-y-4">
      <p className="text-[11px] uppercase tracking-[0.4em] text-slate-500">Parámetros generales</p>
      <div className="grid md:grid-cols-3 gap-5">
        <div>
          <label className="label">L. máxima barra</label>
          <div className="flex gap-2">
            {lengthOptions.map((length) => (
              <button
                type="button"
                key={length}
                onClick={() => setValue('max_rebar_length_m', length, { shouldDirty: true })}
                className={`flex-1 py-2 rounded-lg border text-sm font-semibold transition-colors ${
                  selectedLength === length ? 'bg-primary/90 text-white border-primary' : 'bg-transparent border-slate-700 text-slate-300'
                }`}
              >
                {length}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="label">Gancho</label>
          <select className="input" {...register('hook_type')}>
            {hookOptions.map((hook) => (
              <option key={hook.value} value={hook.value}>
                {hook.label}
              </option>
            ))}
          </select>
          {renderError('hook_type')}
        </div>
        <div>
          <label className="label">Recubrimiento (cm)</label>
          <input type="number" min={1} step={1} className="input" {...register('cover_cm', { valueAsNumber: true })} />
          {renderError('cover_cm')}
        </div>
      </div>
    </div>

    <div className="rounded-3xl border border-slate-800 bg-[#040a16]/50 p-5 space-y-5">
      <p className="text-[11px] uppercase tracking-[0.4em] text-slate-500">Barras Constantes a lo largo de la Viga</p>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-slate-800 bg-[#050b16]/40 p-4 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="label">Barras superiores</p>
              <p className="text-xs text-slate-400">Total: {totalTopBars} barras</p>
            </div>
            <button
              type="button"
              onClick={() => appendTopBarGroup({ quantity: 1, diameter: diameterOptions[0] })}
              className="text-xs uppercase tracking-[0.3em] text-primary"
            >
              + Añadir barras
            </button>
          </div>
          {topBarFields.length === 0 ? (
            <p className="text-xs text-slate-500">Configura al menos un grupo para definir el acero superior.</p>
          ) : (
            <div className="space-y-3">
              {topBarFields.map((field, index) => (
                <div key={field.id} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] gap-3 items-end">
                  <div>
                    <label className="label">Cantidad</label>
                    <input
                      type="number"
                      min={1}
                      className="input input-compact"
                      {...register(`top_bars_config.${index}.quantity`, { valueAsNumber: true })}
                    />
                    {errors.top_bars_config?.[index]?.quantity && (
                      <p className="text-rose-400 text-xs mt-1">{errors.top_bars_config[index].quantity.message}</p>
                    )}
                  </div>
                  <div>
                    <label className="label">Diámetro</label>
                    <select className="input input-compact" {...register(`top_bars_config.${index}.diameter`)}>
                      {diameterOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                    {errors.top_bars_config?.[index]?.diameter && (
                      <p className="text-rose-400 text-xs mt-1">{errors.top_bars_config[index].diameter.message}</p>
                    )}
                  </div>
                  {topBarFields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeTopBarGroup(index)}
                      className="text-xs uppercase tracking-[0.3em] text-slate-500 hover:text-slate-200"
                    >
                      Quitar
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          {topBarsGroupError && <p className="text-rose-400 text-xs">{topBarsGroupError}</p>}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-[#050b16]/40 p-4 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="label">Barras inferiores</p>
              <p className="text-xs text-slate-400">Total: {totalBottomBars} barras</p>
            </div>
            <button
              type="button"
              onClick={() => appendBottomBarGroup({ quantity: 1, diameter: diameterOptions[0] })}
              className="text-xs uppercase tracking-[0.3em] text-primary"
            >
              + Añadir barras
            </button>
          </div>
          {bottomBarFields.length === 0 ? (
            <p className="text-xs text-slate-500">Detalla cada grupo de barras inferiores según el refuerzo.</p>
          ) : (
            <div className="space-y-3">
              {bottomBarFields.map((field, index) => (
                <div key={field.id} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] gap-3 items-end">
                  <div>
                    <label className="label">Cantidad</label>
                    <input
                      type="number"
                      min={1}
                      className="input input-compact"
                      {...register(`bottom_bars_config.${index}.quantity`, { valueAsNumber: true })}
                    />
                    {errors.bottom_bars_config?.[index]?.quantity && (
                      <p className="text-rose-400 text-xs mt-1">{errors.bottom_bars_config[index].quantity.message}</p>
                    )}
                  </div>
                  <div>
                    <label className="label">Diámetro</label>
                    <select className="input input-compact" {...register(`bottom_bars_config.${index}.diameter`)}>
                      {diameterOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                    {errors.bottom_bars_config?.[index]?.diameter && (
                      <p className="text-rose-400 text-xs mt-1">{errors.bottom_bars_config[index].diameter.message}</p>
                    )}
                  </div>
                  {bottomBarFields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeBottomBarGroup(index)}
                      className="text-xs uppercase tracking-[0.3em] text-slate-500 hover:text-slate-200"
                    >
                      Quitar
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          {bottomBarsGroupError && <p className="text-rose-400 text-xs">{bottomBarsGroupError}</p>}
        </div>
      </div>
    </div>

    <div className="grid md:grid-cols-2 gap-6">
      <div>
        <label className="label">Longitud mínima de traslapo (m)</label>
        <input
          type="number"
          step="0.01"
          min="0"
          lang="en"
          inputMode="decimal"
          className="input"
          {...register('lap_splice_length_min_m', { valueAsNumber: true })}
        />
        {renderError('lap_splice_length_min_m')}
      </div>
      <div>
        <label className="label">Ubicación del traslapo</label>
        <input className="input" {...register('lap_splice_location')} />
        {renderError('lap_splice_location')}
      </div>
    </div>

    <div className="bg-[#0b172f] rounded-3xl border border-slate-800 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">Estribos</h2>
        <button
          type="button"
          onClick={() => appendStirrup({ zone: '', spacing_m: '', quantity: '' })}
          className="text-xs uppercase tracking-[0.3em] text-primary"
        >
          + Añadir zona
        </button>
      </div>
      <div className="space-y-3">
        {stirrupFields.map((field, index) => (
          <div key={field.id} className="grid md:grid-cols-3 gap-3 items-end">
            <div>
              <label className="label">Zona</label>
              <input className="input" {...register(`stirrups_config.${index}.zone`)} />
              {errors.stirrups_config?.[index]?.zone && (
                <p className="text-rose-400 text-xs mt-1">{errors.stirrups_config[index].zone.message}</p>
              )}
            </div>
            <div>
              <label className="label">Espaciamiento (m)</label>
              <input
                type="number"
                step="0.01"
                lang="en"
                inputMode="decimal"
                className="input"
                {...register(`stirrups_config.${index}.spacing_m`, { valueAsNumber: true })}
              />
            </div>
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label className="label">Cantidad</label>
                <input
                  type="number"
                  className="input"
                  {...register(`stirrups_config.${index}.quantity`, { valueAsNumber: true })}
                />
              </div>
              {stirrupFields.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeStirrup(index)}
                  className="text-xs uppercase tracking-[0.3em] text-slate-400"
                >
                  Quitar
                </button>
              )}
            </div>
          </div>
        ))}
        {errors.stirrups_config?.message && <p className="text-rose-400 text-xs">{errors.stirrups_config.message}</p>}
      </div>
    </div>
  </div>
);

export default BlockReinforcement;
