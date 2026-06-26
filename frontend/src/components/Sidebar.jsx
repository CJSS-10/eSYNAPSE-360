import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { ChevronsLeft, ChevronsRight, Atom } from 'lucide-react'
import { GRUPOS_MODULOS } from '../lib/modulos.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfig } from '../context/ConfigContext.jsx'

export default function Sidebar() {
  const [colapsado, setColapsado] = useState(false)
  const { usuario, tienePermiso } = useAuth()
  const { config } = useConfig()
  const habilitados = new Set(config.modulos_habilitados || [])
  const esAdmin = usuario?.is_superuser || (usuario?.roles || []).includes('Administrador del Sistema')

  const visible = (item) => {
    if (item.libre || item.clave === 'dashboard') return true
    const modulo = item.modulo || item.clave
    // Licenciamiento: módulo no habilitado en esta instalación → oculto
    if (habilitados.size > 0 && !habilitados.has(modulo)) return false
    if (item.fase !== 0) return true // se muestra deshabilitado
    if (item.soloAdmin) return esAdmin
    return tienePermiso(modulo, 'leer')
  }

  return (
    <aside
      className={`flex h-screen shrink-0 flex-col border-r border-slate-200 bg-white transition-all
        duration-200 dark:border-slate-800 dark:bg-slate-900 ${colapsado ? 'w-16' : 'w-64'}`}
    >
      {/* Marca */}
      <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-4 dark:border-slate-800">
        {config.logo_url
          ? <img src={config.logo_url} alt="logo" className={`${colapsado ? 'h-8 w-8' : 'h-10 w-10'} shrink-0 rounded object-contain`} />
          : <Atom className={`${colapsado ? 'h-8 w-8' : 'h-9 w-9'} shrink-0 text-esynapse-500`} />}
        {!colapsado && (
          <div className="leading-tight">
            <p className="text-sm font-bold tracking-wide">{config.nombre_corto || 'eSYNAPSE 360°'}</p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400">{config.subtitulo}</p>
          </div>
        )}
      </div>

      {/* Módulos */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {GRUPOS_MODULOS.map((grupo) => (
          <div key={grupo.titulo} className="mb-4">
            {!colapsado && (
              <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                {grupo.titulo}
              </p>
            )}
            <ul className="space-y-0.5">
              {grupo.items.filter(visible).map((item) => {
                const Icono = item.icono
                const habilitado = item.fase === 0
                if (!habilitado) {
                  return (
                    <li key={item.clave}>
                      <div
                        title={`${item.nombre} — disponible en Fase ${item.fase}`}
                        className="flex cursor-not-allowed items-center gap-3 rounded-lg px-2 py-1.5
                          text-sm text-slate-400 opacity-60 dark:text-slate-600"
                      >
                        <Icono className="h-4 w-4 shrink-0" />
                        {!colapsado && (
                          <span className="flex-1 truncate">{item.nombre}</span>
                        )}
                        {!colapsado && (
                          <span className="rounded bg-slate-200 px-1 text-[9px] font-medium dark:bg-slate-800">
                            F{item.fase}
                          </span>
                        )}
                      </div>
                    </li>
                  )
                }
                return (
                  <li key={item.clave}>
                    <NavLink
                      to={item.ruta}
                      end={item.ruta === '/'}
                      title={item.nombre}
                      className={({ isActive }) =>
                        `flex items-center gap-3 rounded-lg px-2 py-1.5 text-sm transition ${
                          isActive
                            ? 'bg-esynapse-600/15 font-medium text-esynapse-600 dark:bg-esynapse-500/15 dark:text-esynapse-300'
                            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                        }`
                      }
                    >
                      <Icono className="h-4 w-4 shrink-0" />
                      {!colapsado && <span className="truncate">{item.nombre}</span>}
                    </NavLink>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Colapsar */}
      <button
        onClick={() => setColapsado(!colapsado)}
        className="flex h-11 items-center justify-center border-t border-slate-200 text-slate-500
          transition hover:bg-slate-100 dark:border-slate-800 dark:hover:bg-slate-800"
        title={colapsado ? 'Expandir' : 'Colapsar'}
      >
        {colapsado ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
      </button>
    </aside>
  )
}
