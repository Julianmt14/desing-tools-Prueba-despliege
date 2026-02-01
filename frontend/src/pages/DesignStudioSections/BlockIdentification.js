import React from 'react';

const BlockIdentification = ({ register, renderError, elementLevelField, handleLevelBlur, energyOptions }) => (
  <div className="space-y-6 bg-[#050b16]/40 border border-slate-800 rounded-3xl p-6 shadow-[0_14px_45px_rgba(5,11,22,0.6)]">
    <header className="flex items-center justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Bloque 01</p>
        <h2 className="text-lg font-semibold">Identificación y materiales</h2>
      </div>
      <span className="text-xs text-slate-400">Proyecto · f’c · fy · DES</span>
    </header>

    <div className="grid md:grid-cols-2 gap-6">
      <div>
        <label className="label">Proyecto</label>
        <input className="input" placeholder="Nombre del proyecto" {...register('project_name')} />
        {renderError('project_name')}
      </div>
      <div>
        <label className="label">Viga / Identificador</label>
        <input className="input" {...register('beam_label')} />
        {renderError('beam_label')}
      </div>
      <div>
        <label className="label">Nivel (m)</label>
        <input
          type="number"
          step="0.01"
          lang="en"
          inputMode="decimal"
          className="input no-spin"
          {...elementLevelField}
          onBlur={(event) => {
            elementLevelField.onBlur(event);
            handleLevelBlur(event);
          }}
        />
        {renderError('element_level')}
      </div>
      <div>
        <label className="label">Cantidad de elementos</label>
        <input type="number" className="input" min={1} {...register('element_quantity', { valueAsNumber: true })} />
        {renderError('element_quantity')}
      </div>
    </div>

    <div className="grid md:grid-cols-3 gap-6">
      <div>
        <label className="label">f’c concreto</label>
        <select className="input" {...register('concrete_strength')}>
          <option value="21 MPa (3000 psi)">21 MPa (3000 psi)</option>
          <option value="24 MPa (3500 psi)">24 MPa (3500 psi)</option>
          <option value="28 MPa (4000 psi)">28 MPa (4000 psi)</option>
          <option value="32 MPa (4600 psi)">32 MPa (4600 psi)</option>
        </select>
        {renderError('concrete_strength')}
      </div>
      <div>
        <label className="label">fy refuerzo</label>
        <select className="input" {...register('reinforcement')}>
          <option value="420 MPa (Grado 60)">420 MPa (Grado 60)</option>
          <option value="520 MPa (Grado 75)">520 MPa (Grado 75)</option>
        </select>
        {renderError('reinforcement')}
      </div>
      <div>
        <label className="label">Clase de disipación</label>
        <select className="input" {...register('energy_dissipation_class')}>
          {energyOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
    </div>
  </div>
);

export default BlockIdentification;
