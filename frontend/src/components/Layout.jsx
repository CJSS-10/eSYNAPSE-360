import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence, MotionConfig } from 'framer-motion'
import {
  AlertOctagon, Bell, Calendar, CheckCheck, ClipboardList, FileText, LogOut, Moon, Ruler, Sun, Wrench,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import Sidebar from './Sidebar.jsx'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'

const ICONO_MODULO = {
  'Hallazgos': AlertOctagon, 'Acciones Correctivas': Wrench, 'Documentos': FileText, 'Auditorías': ClipboardList, 'Equipos': Ruler,
}

const iniciales = (nombre) =>
  (nombre || '?').trim().split(/\s+/).slice(0, 2).map((s) => s[0] || '').join('').toUpperCase() || '?'

const claveTarea = (t) => `${t.modulo}|${t.codigo}|${t.estado}|${t.fecha || ''}`
const leerLeidas = () => {
  try { return new Set(JSON.parse(localStorage.getItem('esynapse_tareas_leidas') || '[]')) } catch { return new Set() }
}
const guardarLeidas = (set) => localStorage.setItem('esynapse_tareas_leidas', JSON.stringify([...set]))

export default function Layout() {
  const { usuario, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [oscuro, setOscuro] = useState(document.documentElement.classList.contains('dark'))
  const [tareas, setTareas] = useState([])
  const [leidas, setLeidas] = useState(leerLeidas)
  const [abierto, setAbierto] = useState(false)
  const buzonRef = useRef(null)

  const alternarTema = () => {
    const nuevo = !oscuro
    setOscuro(nuevo)
    document.documentElement.classList.toggle('dark', nuevo)
    localStorage.setItem('esynapse_tema', nuevo ? 'dark' : 'light')
  }

  const cargarTareas = () => {
    api.misTareas().then((d) => {
      const t = d.tareas || []
      setTareas(t)
      const claves = new Set(t.map(claveTarea))
      setLeidas((prev) => {
        const filtrado = new Set([...prev].filter((k) => claves.has(k)))
        guardarLeidas(filtrado)
        return filtrado
      })
    }).catch(() => {})
  }

  useEffect(() => {
    cargarTareas()
    const t = setInterval(cargarTareas, 120000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    const fuera = (e) => { if (buzonRef.current && !buzonRef.current.contains(e.target)) setAbierto(false) }
    document.addEventListener('mousedown', fuera)
    return () => document.removeEventListener('mousedown', fuera)
  }, [])

  const noLeidas = tareas.filter((t) => !leidas.has(claveTarea(t)))

  const marcarLeida = (t) => {
    setLeidas((prev) => { const s = new Set(prev); s.add(claveTarea(t)); guardarLeidas(s); return s })
  }
  const marcarTodas = () => {
    const s = new Set(tareas.map(claveTarea)); guardarLeidas(s); setLeidas(s)
  }
  const irA = (ruta, t) => { if (t) marcarLeida(t); setAbierto(false); navigate(ruta) }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-end gap-3 border-b border-slate-200 bg-white px-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="relative" ref={buzonRef}>
            <button
              onClick={() => { setAbierto(!abierto); if (!abierto) cargarTareas() }}
              className="relative rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-800"
              title="Notificaciones"
              aria-label="Notificaciones"
            >
              <Bell className="h-4 w-4" />
              {noLeidas.length > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">
                  {noLeidas.length > 99 ? '99+' : noLeidas.length}
                </span>
              )}
            </button>
            {abierto && (
              <div className="absolute right-0 top-11 z-50 max-h-96 w-80 overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-pop dark:border-slate-800 dark:bg-slate-900">
                <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2 dark:border-slate-800">
                  <p className="text-sm font-semibold">Notificaciones</p>
                  {noLeidas.length > 0 && (
                    <button onClick={marcarTodas} title="Marcar todas como leídas"
                      className="flex items-center gap-1 text-[10px] font-medium text-esynapse-600 hover:underline dark:text-esynapse-300">
                      <CheckCheck className="h-3 w-3" /> Marcar todas
                    </button>
                  )}
                </div>
                {noLeidas.length === 0 ? (
                  <p className="px-3 py-6 text-center text-xs text-slate-400">Estás al día. Sin pendientes.</p>
                ) : (
                  <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                    {noLeidas.slice(0, 8).map((t, i) => {
                      const Ico = ICONO_MODULO[t.modulo] || Bell
                      return (
                        <li key={i}>
                          <button onClick={() => irA(t.ruta, t)} className="flex w-full items-start gap-2.5 px-3 py-2 text-left transition hover:bg-slate-50 dark:hover:bg-slate-800/60">
                            <Ico className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-xs font-medium">{t.codigo} <span className="font-normal text-slate-400">· {t.estado}</span></span>
                              <span className="block truncate text-[11px] text-slate-500 dark:text-slate-400">{t.titulo}</span>
                              {t.fecha && <span className="flex items-center gap-1 text-[10px] text-amber-600 dark:text-amber-400"><Calendar className="h-2.5 w-2.5" /> {t.fecha}</span>}
                            </span>
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                )}
                <button onClick={() => irA('/mis-tareas')} className="block w-full border-t border-slate-100 px-3 py-2 text-center text-xs font-medium text-esynapse-600 hover:bg-slate-50 dark:border-slate-800 dark:text-esynapse-300 dark:hover:bg-slate-800/60">
                  Ver todas mis tareas
                </button>
              </div>
            )}
          </div>

          <button
            onClick={alternarTema}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-800"
            title={oscuro ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
            aria-label={oscuro ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
          >
            {oscuro ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <div className="mx-1 h-6 w-px bg-slate-200 dark:bg-slate-700" />
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-esynapse-600 text-xs font-bold text-white shadow-sm">
              {iniciales(usuario?.nombre_completo || usuario?.username)}
            </div>
            <div className="hidden text-right leading-tight sm:block">
              <p className="text-sm font-medium">{usuario?.nombre_completo || usuario?.username}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {usuario?.cargo || (usuario?.is_superuser ? 'Superusuario' : '')}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-red-500/10 hover:text-red-500"
            title="Cerrar sesión"
            aria-label="Cerrar sesión"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <MotionConfig reducedMotion="user">
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </MotionConfig>
        </main>
      </div>
    </div>
  )
}
