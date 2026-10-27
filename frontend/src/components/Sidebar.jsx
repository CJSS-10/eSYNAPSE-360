import { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { ChevronDown, ChevronsLeft, ChevronsRight, Atom, Lock } from 'lucide-react'
import { GRUPOS_MODULOS } from '../lib/modulos.js'
import { useIndicador } from '../lib/movimiento.js'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useConfig } from '../context/ConfigContext.jsx'

// Menú lateral (ADR-0007): grupos por área de trabajo, con los pendientes de cada módulo al lado.
// Los módulos aún no construidos se reúnen al final en «Por construir», plegado.
const lista = (r) => (r?.results ?? r ?? [])

export default function Sidebar() {
  const [colapsado, setColapsado] = useState(false)
  const [verFuturos, setVerFuturos] = useState(false)
  const [conteos, setConteos] = useState({})
  const { usuario, tienePermiso } = useAuth()
  const { config } = useConfig()
  const location = useLocation()
  const navRef = useRef(null)
  const habilitados = new Set(config.modulos_habilitados || [])
  const esAdmin = usuario?.is_superuser || (usuario?.roles || []).includes('Administrador del Sistema')

  const visible = (item) => {
    if (item.libre || item.clave === 'dashboard') return true
    const modulo = item.modulo || item.clave
    if (habilitados.size > 0 && !habilitados.has(modulo)) return false   // licenciamiento
    if (item.fase !== 0) return true
    if (item.soloAdmin) return esAdmin
    return tienePermiso(modulo, 'leer')
  }

  // Pendientes por módulo: tus tareas, hallazgos abiertos, solicitudes y quejas abiertas.
  useEffect(() => {
    let vivo = true
    const cargar = () => {
      const pedidos = [
        ['mis_tareas', api.misTareas().then((d) => (d.tareas || []).length)],
        tienePermiso('hallazgos', 'leer') && ['hallazgos', api.hallazgos.resumen().then((d) => d.abiertos)],
        tienePermiso('acciones_correctivas', 'leer') && ['acciones_correctivas', api.sac.listar('?abiertas=1').then((d) => lista(d).length)],
        tienePermiso('quejas', 'leer') && ['quejas', api.quejas.listar('?abiertas=1').then((d) => lista(d).length)],
      ].filter(Boolean)
      Promise.allSettled(pedidos.map(([, p]) => p)).then((rs) => {
        if (!vivo) return
        const c = {}
        rs.forEach((r, i) => { if (r.status === 'fulfilled' && r.value) c[pedidos[i][0]] = r.value })
        setConteos(c)
      })
    }
    cargar()
    const t = setInterval(cargar, 120000)
    return () => { vivo = false; clearInterval(t) }
  }, [location.pathname])  // eslint-disable-line react-hooks/exhaustive-deps

  const grupos = GRUPOS_MODULOS
    .map((g) => ({ ...g, activos: g.items.filter((i) => i.fase === 0 && visible(i)) }))
    .filter((g) => g.activos.length > 0)
  const futuros = GRUPOS_MODULOS.flatMap((g) => g.items.filter((i) => i.fase !== 0 && visible(i)))
  // La selección del menú se desliza hasta la opción activa (movimiento, 27-10-2026)
  const sel = useIndicador(navRef, 'a[aria-current="page"]', `${location.pathname}|${colapsado}|${verFuturos}|${Object.keys(conteos).length}`)

  return (
    <aside
      className={`flex h-screen shrink-0 flex-col border-r border-slate-200 bg-white transition-all
        duration-200 dark:border-slate-800 dark:bg-slate-900 ${colapsado ? 'w-16' : 'w-64'}`}
    >
      {/* Marca */}
      <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-4 dark:border-slate-800">
        {config.logo_url
          ? <img src={config.logo_url} alt="" className={`${colapsado ? 'h-8 w-8' : 'h-10 w-10'} shrink-0 rounded object-contain`} />
          : <Atom className={`${colapsado ? 'h-8 w-8' : 'h-9 w-9'} shrink-0 text-esynapse-500`} />}
        {!colapsado && (
          <div className="leading-tight">
            <p className="text-sm font-bold">{config.nombre_corto || 'eSYNAPSE 360°'}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">{config.subtitulo}</p>
          </div>
        )}
      </div>

      <nav ref={navRef} aria-label="Menú principal" className="relative flex-1 overflow-y-auto px-2 py-3">
        {sel && (
          <span aria-hidden="true" className="mov-indicador pointer-events-none absolute rounded-lg bg-esynapse-600/15 dark:bg-esynapse-500/15"
            style={{ left: sel.left, top: sel.top, width: sel.width, height: sel.height }} />
        )}
        {grupos.map((grupo) => (
          <div key={grupo.titulo} className="mb-4">
            {!colapsado && (
              <p className="px-2 pb-1 text-xs font-semibold text-slate-500 dark:text-slate-400">{grupo.titulo}</p>
            )}
            <ul className="space-y-0.5">
              {grupo.activos.map((item) => {
                const Icono = item.icono
                const n = conteos[item.clave]
                return (
                  <li key={item.clave}>
                    <NavLink
                      to={item.ruta}
                      end={item.ruta === '/'}
                      title={item.nombre}
                      className={({ isActive }) =>
                        `relative flex items-center gap-3 rounded-lg px-2 py-2 text-sm transition-colors ${
                          isActive
                            ? 'font-semibold text-esynapse-700 dark:text-esynapse-300'
                            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white'
                        }`
                      }
                    >
                      <Icono className="h-4 w-4 shrink-0" />
                      {!colapsado && <span className="flex-1 truncate">{item.nombre}</span>}
                      {!colapsado && n > 0 && (
                        <span key={n} className="mov-rebote rounded-full bg-slate-100 px-1.5 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                          aria-label={`${n} pendientes`}>{n > 99 ? '99+' : n}</span>
                      )}
                    </NavLink>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}

        {futuros.length > 0 && !colapsado && (
          <div className="border-t border-slate-200 pt-2 dark:border-slate-800">
            <button type="button" onClick={() => setVerFuturos(!verFuturos)} aria-expanded={verFuturos}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs font-semibold text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800">
              <Lock className="h-3.5 w-3.5" />
              <span className="flex-1">Por construir ({futuros.length})</span>
              <ChevronDown className={`h-3.5 w-3.5 transition-transform ${verFuturos ? 'rotate-180' : ''}`} />
            </button>
            <div className="mov-acordeon" style={{ gridTemplateRows: verFuturos ? '1fr' : '0fr' }} aria-hidden={!verFuturos}>
              <ul className="mt-1 space-y-0.5">
                {futuros.map((item) => {
                  const Icono = item.icono
                  return (
                    <li key={item.clave} title={`Disponible en la fase ${item.fase}`}
                      className="flex items-center gap-3 px-2 py-1.5 text-sm text-slate-400 dark:text-slate-500">
                      <Icono className="h-4 w-4 shrink-0" />
                      <span className="flex-1 truncate">{item.nombre}</span>
                      <span className="text-xs">Fase {item.fase}</span>
                    </li>
                  )
                })}
              </ul>
            </div>
          </div>
        )}
      </nav>

      <button
        onClick={() => setColapsado(!colapsado)}
        className="flex h-11 items-center justify-center border-t border-slate-200 text-slate-500
          transition hover:bg-slate-100 dark:border-slate-800 dark:hover:bg-slate-800"
        title={colapsado ? 'Expandir el menú' : 'Contraer el menú'}
        aria-label={colapsado ? 'Expandir el menú' : 'Contraer el menú'}
      >
        {colapsado ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
      </button>
    </aside>
  )
}
