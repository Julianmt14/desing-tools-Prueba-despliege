import React from 'react';
import { useNavigate } from 'react-router-dom';

const directTools = [
  { name: 'Despiece de Vigas', icon: 'rebase_edit', color: 'text-primary', path: '/tools/despiece-de-vigas' },
  { name: 'Cuadro de Fierros', icon: 'grid_on', color: 'text-amber-500', path: '/tools/cuadro-de-fierros' },
  { name: 'Sincronización BIM', icon: 'layers', color: 'text-green-500', path: '/tools/sincronizacion-bim' },
];

const recentProjects = [
  {
    id: 1,
    name: 'Torre B - Cimentación',
    date: 'Modificado hace 2h',
    status: 'Sincronizado con Revit',
    statusColor: 'bg-green-500/90',
    statusIcon: 'cloud_done',
    software: 'Revit 2024',
    softwareIcon: 'hub',
    image:
      'https://lh3.googleusercontent.com/aida-public/AB6AXuBCP3DeBL3kbp0tsBAG3d-qgL_fwomdKXm-G8sRlgPYNi9m6PhvXNGrSpTzkLI-HBy4cJRi4wj3Rcfcs7tZkgrP2uqkTsf89WlDqSuQnzLYkIsw1uqQXecc0ZDrKlKbeveHkKNpU_fFGSQBddGQ9jwAdE_b7t5O4wIKAISZbd824gr9XdgJaHDTOKL51CTfAHOH8Vma9hqgm75FlJaZDQ80N2josT201HwsN6t216GzI2XSMwpP9LFjJY1ZAfHVU5ii6GsTBUvynkk',
  },
  {
    id: 2,
    name: 'Puente Colgante - Sección',
    date: 'Modificado hace 5h',
    status: 'Borrador',
    statusColor: 'bg-amber-500/90',
    statusIcon: 'edit_note',
    software: 'Guardado Local',
    softwareIcon: 'sync_disabled',
    image:
      'https://lh3.googleusercontent.com/aida-public/AB6AXuCQJZdFIgdUyYo96Soc6yiBFAhpL6LW_tNZRE7bRmTx943PaoxYEx6HGQv7YRmxlBFfIdEjltL_c9QwFI2_CczMnhQQIowIQpT66VnK1TXJBUScldqGmMfTQuhsYWVgIh1zurvJmwxFWCnKySrgHfKSj1eyxejx1__umkqZ1WKhpvfwp0WDBRqd8Rd6pKXKefRngvQHdeFkAmK_5Zl8j4S-NUjF6hCQfTJcJAVWkQznZ9PndqOusapPhZhdWrCEA2BiGD3qg1BDnSA',
  },
  {
    id: 3,
    name: 'Detalle Refuerzo Ala Este',
    date: 'Modificado ayer',
    status: 'Sincronizado con Revit',
    statusColor: 'bg-green-500/90',
    statusIcon: 'cloud_done',
    software: 'Enlace AutoCAD',
    softwareIcon: 'hub',
    image:
      'https://lh3.googleusercontent.com/aida-public/AB6AXuBz4bBPo3FJ4OzkGQenmjhLTD0MXoiPjAhFMDqpg6oY3QWXhKuaaKmBDQ8uALF9ReT4hRfEx_E2wiQk6vpc6Jf8v52W1PKDZ9DVNwpNzE_-eCskjRcnE8L483TTI1XMmogfgTDU2FxPFB1YuZ7KfXIIEi_x3yO8wKfKqn_K6F7pnYEpnYI66wUyaI67EWMXatcNRO-H1SBX8pQHiOwEPmZlP9WXjQBMKQoyIKPx8nq4FZoRqr6AY76oIanCkiHzUOjDJuXPTQ4ACE0',
  },
];

const bottomNavItems = [
  { label: 'Proyectos', icon: 'dashboard', active: true, path: '/' },
  { label: 'Sincronización', icon: 'sync', active: false, path: '/sincronizacion' },
  { label: 'Biblioteca', icon: 'library_books', active: false, path: '/biblioteca' },
  { label: 'Configuración', icon: 'settings', active: false, path: '/configuracion' },
];

const Dashboard = () => {
  const navigate = useNavigate();

  const goToTool = (path) => {
    navigate(path);
  };

  return (
    <div
      className="min-h-screen pb-24"
      style={{ backgroundColor: '#0b1120', color: '#e2e8f0' }}
    >
      <nav
        className="sticky top-0 z-50 backdrop-blur-md border-b border-[#1c2436]"
        style={{ backgroundColor: 'rgba(7, 12, 24, 0.95)' }}
      >
        <div className="flex items-center p-4 justify-between max-w-xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="bg-primary p-1.5 rounded-lg flex items-center justify-center">
              <span className="material-symbols-outlined text-white text-[20px]">architecture</span>
            </div>
            <h2 className="text-white text-lg font-bold leading-tight tracking-tight">Panel de Control</h2>
          </div>
          <button
            type="button"
            className="flex items-center gap-2 px-4 h-10 rounded-full bg-primary text-white shadow-lg shadow-primary/20 active:scale-95 transition-transform"
            onClick={() => navigate('/studio')}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>
              add
            </span>
            <span className="text-sm font-semibold">Nuevo Proyecto</span>
          </button>
        </div>
      </nav>

      <div className="max-w-xl mx-auto px-4 py-3">
        <label className="flex flex-col min-w-40 h-12 w-full">
          <div className="flex w-full flex-1 items-stretch rounded-xl h-full shadow-sm">
            <div className="text-[#92a4c9] flex border-none bg-[#111a2b] items-center justify-center pl-4 rounded-l-xl">
              <span className="material-symbols-outlined">search</span>
            </div>
            <input
              className="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-r-xl text-slate-100 focus:outline-0 focus:ring-0 border-none bg-[#111a2b] h-full placeholder:text-[#7f8fb5] px-4 pl-2 text-base font-normal leading-normal"
              placeholder="Buscar proyecto..."
            />
          </div>
        </label>

        <div className="mt-4 mb-2">
          <p className="text-[11px] font-bold uppercase tracking-[0.1em] text-[#8ea2d6] mb-3 px-1">Herramientas Directas</p>
          <div className="flex gap-3 overflow-x-auto no-scrollbar pb-2">
            {directTools.map((tool) => (
              <button
                type="button"
                key={tool.name}
                className="flex h-10 shrink-0 items-center justify-center gap-x-2 rounded-xl bg-[#111a2b] px-4 border border-[#1f2a3d] shadow-sm active:scale-95 transition-transform"
                onClick={() => goToTool(tool.path)}
              >
                <span className={`material-symbols-outlined ${tool.color} text-[20px]`}>{tool.icon}</span>
                <p className="text-slate-100 text-sm font-semibold">{tool.name}</p>
              </button>
            ))}
          </div>
        </div>
      </div>

      <main className="max-w-xl mx-auto px-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white text-lg font-bold leading-tight tracking-tight">Proyectos Recientes</h3>
          <span
            className="text-primary text-sm font-semibold cursor-pointer"
            onClick={() => navigate('/designs')}
          >
            Ver Todo
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 pb-8">
          {recentProjects.map((project) => (
            <article
              key={project.id}
              className="flex flex-col rounded-xl overflow-hidden bg-[#121b2d] border border-[#1f2a3d] shadow-sm"
            >
              <div
                className="w-full bg-center bg-no-repeat aspect-[16/9] bg-cover relative"
                style={{ backgroundImage: `url('${project.image}')` }}
              >
                <div
                  className={`absolute top-3 right-3 ${project.statusColor} backdrop-blur-sm text-white text-[10px] font-bold px-2 py-0.5 rounded flex items-center gap-1 uppercase tracking-wider`}
                >
                  <span className="material-symbols-outlined text-[12px]">{project.statusIcon}</span>
                  {project.status}
                </div>
              </div>

              <div className="flex flex-col gap-2 p-4">
                <div>
                  <p className="text-white text-lg font-bold leading-tight">{project.name}</p>
                  <p className="text-slate-400 text-sm font-normal mt-0.5 flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">schedule</span>
                    {project.date}
                  </p>
                </div>

                <div className="flex items-center gap-3 justify-between mt-2 pt-3 border-t border-[#1f2a3d]">
                  <div className="flex items-center gap-2">
                    <span
                      className={`material-symbols-outlined ${
                        project.softwareIcon === 'sync_disabled' ? 'text-slate-500' : 'text-primary'
                      } text-[20px]`}
                    >
                      {project.softwareIcon}
                    </span>
                    <p className="text-slate-300 text-sm font-medium">{project.software}</p>
                  </div>
                  <button
                    type="button"
                    className="flex items-center justify-center rounded-lg h-9 px-5 bg-primary text-white text-sm font-bold shadow-sm active:scale-95 transition-transform"
                    onClick={() => navigate(`/project/${project.id}`)}
                  >
                    Abrir Editor
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </main>

      <div className="fixed bottom-0 left-0 right-0 z-50 bg-[#141c2c]/90 backdrop-blur-xl border-t border-[#1f2a3d] pb-8 pt-2">
        <div className="max-w-xl mx-auto flex justify-around items-center px-4">
          {bottomNavItems.map((item) => (
            <button
              type="button"
              key={item.label}
              className={`flex flex-col items-center gap-1 ${item.active ? 'text-primary' : 'text-[#7b8dbb]'}`}
              onClick={() => navigate(item.path)}
            >
              <span
                className="material-symbols-outlined"
                style={{ fontVariationSettings: item.active ? "'FILL' 1" : "'FILL' 0" }}
              >
                {item.icon}
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider">{item.label}</span>
            </button>
          ))}
        </div>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

        .material-symbols-outlined {
          font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }

        .no-scrollbar::-webkit-scrollbar {
          display: none;
        }

        .no-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>

      <style>{`
        :root {
          --primary: #135bec;
          --background-light: #f6f6f8;
          --background-dark: #101622;
        }

        .bg-primary {
          background-color: var(--primary);
        }

        .text-primary {
          color: var(--primary);
        }

        .bg-background-light {
          background-color: var(--background-light);
        }

        .bg-background-dark {
          background-color: var(--background-dark);
        }

        .shadow-primary\/20 {
          box-shadow: 0 10px 15px -3px rgba(19, 91, 236, 0.2);
        }
      `}</style>
    </div>
  );
};

export default Dashboard;