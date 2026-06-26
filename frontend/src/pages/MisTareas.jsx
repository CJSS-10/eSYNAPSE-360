import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, ChevronRight } from 'lucide-react'
import { api } from '../lib/api.js'

const ICONO = { 'Hallazgos': '🔎', 'Acciones Correctivas': '🔧', 'Documentos': '📄', 'Auditorías': '📋' }
const ORDEN = ['Hallazgos', 'Acciones Correctivas', 'Documentos', 'Auditorías']

export default function MisTareas() {
  const navigate = useNavigate()
  const [tareas, setTareas] = useState([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    api.misTareas().then((d) => setTareas(d.tareas || [])).catch(() => {}).finally(() => setCargando(false))
  }, [])

  const grupos = {}
  tareas.forEach((t) => { (grupos[t.modulo] = grupos[t.modulo] || []).push(t) })
  const modulos = Object.keys(grupos).sort((a, b) => ORDEN.indexOf(a) - ORDEN.indexOf(b))

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Bell className="h-6 w-6 text-esynapse-500" />
        <h1 className="text-2xl font-bold">Mis tareas</h1>
        <span className="rounded-full bg-esynapse-600/15 px-2 py-0.5 text-xs font-medium text-esynapse-600 dark:text-esynapse-300">{tareas.length}</span>
      </div>
      <p className="text-sm text-slate-500 dark:text-slate-400">Todo lo asignado a tu persona a lo largo del sistema, en un solo lugar.</p>

      {cargando ? (
        <p className="text-sm text-slate-400">Cargando…</p>
      ) : tareas.length === 0 ? (
        <div className="card-esynapse p-10 text-center text-slate-400">No tienes tareas pendientes 🎉</div>
      ) : (
        modulos.map((mod) => (
          <div key={mod} className="card-esynapse overflow-hidden">
            <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-2.5 dark:border-slate-800">
              <span className="text-base">{ICONO[mod] || '•'}</span>
              <h2 className="text-sm font-semibold">{mod}</h2>
              <span className="text-xs text-slate-400">({grupos[mod].length})</span>
            </div>
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {grupos[mod].map((t, i) => (
                <li key={i}>
                  <button onClick={() => navigate(t.ruta)} className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm">
                        <span className="font-mono font-medium">{t.codigo}</span>
                        <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500 dark:bg-slate-800 dark:text-slate-400">{t.estado}</span>
                        {t.rol && <span className="ml-1 rounded bg-esynapse-600/15 px-1.5 py-0.5 text-[10px] text-esynapse-600 dark:text-esynapse-300">{t.rol}</span>}
                      </p>
                      <p className="truncate text-xs text-slate-500 dark:text-slate-400">{t.titulo}</p>
                    </div>
                    {t.fecha && <span className="shrink-0 text-xs text-amber-600 dark:text-amber-400">📅 {t.fecha}</span>}
                    <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))
      )}
    </div>
  )
}
