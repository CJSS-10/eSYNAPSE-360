import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { api } from '../lib/api.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'
import Badge, { TONO_ESTADO } from '../components/ui/Badge.jsx'
import { SkeletonText } from '../components/ui/Skeleton.jsx'

// Mis tareas (ADR-0007): ordenadas por urgencia, no por módulo. El módulo va como etiqueta en
// cada tarea; se puede filtrar por módulo cuando hay tareas de más de uno.

// El backend envía algunos nombres con mayúsculas iniciales; la interfaz usa tipo oración.
const NOMBRE_MODULO = { 'Acciones Correctivas': 'Acciones correctivas', 'Competencia Técnica': 'Competencia técnica' }
const GRUPOS = [
  ['vencidas', 'Vencidas', 'text-red-700 dark:text-red-300', 'bg-red-500'],
  ['semana', 'Esta semana', 'text-amber-700 dark:text-amber-300', 'bg-amber-500'],
  ['despues', 'Más adelante', 'text-slate-700 dark:text-slate-200', 'bg-esynapse-600'],
  ['sinplazo', 'Sin plazo', 'text-slate-700 dark:text-slate-200', 'bg-slate-400'],
]

const hoy0 = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d }
const diasHasta = (f) => Math.round((new Date(`${f.slice(0, 10)}T00:00:00`) - hoy0()) / 86400000)
const grupoDe = (t) => {
  if (!t.fecha) return 'sinplazo'
  const d = diasHasta(t.fecha)
  return d < 0 ? 'vencidas' : d <= 7 ? 'semana' : 'despues'
}
const relativo = (f) => {
  const d = diasHasta(f)
  if (d === 0) return 'hoy'
  if (d === 1) return 'mañana'
  if (d === -1) return 'ayer'
  return d < 0 ? `hace ${-d} días` : `en ${d} días`
}
const fechaCorta = (f) => new Date(`${f.slice(0, 10)}T00:00:00`).toLocaleDateString('es-PE', { day: 'numeric', month: 'short' })

export default function MisTareas() {
  const navigate = useNavigate()
  const [tareas, setTareas] = useState([])
  const [cargando, setCargando] = useState(true)
  const [modulo, setModulo] = useState('')

  useEffect(() => {
    api.misTareas()
      .then((d) => setTareas((d.tareas || []).map((t) => ({ ...t, modulo: NOMBRE_MODULO[t.modulo] || t.modulo }))))
      .catch(() => {}).finally(() => setCargando(false))
  }, [])

  const modulos = [...new Set(tareas.map((t) => t.modulo))]
  const visibles = tareas.filter((t) => !modulo || t.modulo === modulo)
  const porGrupo = {}
  visibles.forEach((t) => { (porGrupo[grupoDe(t)] = porGrupo[grupoDe(t)] || []).push(t) })
  Object.values(porGrupo).forEach((l) => l.sort((a, b) => (a.fecha || '').localeCompare(b.fecha || '')))

  return (
    <div className="space-y-5">
      <TituloModulo seccion="General" titulo="Mis tareas"
        descripcion="Todo lo asignado a tu persona en el sistema, ordenado por urgencia: primero lo vencido, luego lo de esta semana." />

      {modulos.length > 1 && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por módulo">
          {['', ...modulos].map((m) => {
            const n = m ? tareas.filter((t) => t.modulo === m).length : tareas.length
            const activo = modulo === m
            return (
              <button key={m || 'todos'} type="button" onClick={() => setModulo(m)} aria-pressed={activo}
                className={`rounded-full border px-3 py-1 text-[13px] transition-colors ${activo
                  ? 'border-esynapse-600 bg-esynapse-600 font-semibold text-white'
                  : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'}`}>
                {m || 'Todas'} <span className={activo ? 'text-white/80' : 'text-slate-400'}>{n}</span>
              </button>
            )
          })}
        </div>
      )}

      {cargando ? (
        <div className="card-esynapse p-5"><SkeletonText lines={5} /></div>
      ) : visibles.length === 0 ? (
        <div className="card-esynapse p-10 text-center">
          <p className="font-semibold">No tienes tareas pendientes</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Cuando te asignen algo en cualquier módulo, aparecerá aquí.</p>
        </div>
      ) : (
        GRUPOS.filter(([k]) => porGrupo[k]?.length).map(([k, nombre, color, punto]) => (
          <section key={k} className="card-esynapse overflow-hidden" aria-labelledby={`g-${k}`}>
            <h2 id={`g-${k}`} className={`flex items-center gap-2 border-b border-slate-200 px-4 py-2.5 text-sm font-semibold dark:border-slate-800 ${color}`}>
              <span className={`h-2 w-2 rounded-full ${punto}`} aria-hidden="true" />
              {nombre}
              <span className="font-normal text-slate-500 dark:text-slate-400">{porGrupo[k].length}</span>
            </h2>
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {porGrupo[k].map((t, i) => (
                <li key={i}>
                  <button onClick={() => navigate(t.ruta)} className="flex w-full items-center gap-4 px-4 py-3 text-left transition hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <span className="w-20 shrink-0">
                      {t.fecha ? (
                        <>
                          <span className={`block text-sm font-semibold ${k === 'vencidas' ? 'text-red-700 dark:text-red-300' : ''}`}>{fechaCorta(t.fecha)}</span>
                          <span className="block text-xs text-slate-500 dark:text-slate-400">{relativo(t.fecha)}</span>
                        </>
                      ) : <span className="text-xs text-slate-500 dark:text-slate-400">—</span>}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-1.5">
                        <span className="font-mono text-sm font-medium">{t.codigo}</span>
                        <Badge tono={TONO_ESTADO[t.estado] || 'gris'}>{t.estado}</Badge>
                        {t.rol && <span className="text-xs text-slate-500 dark:text-slate-400">como {t.rol}</span>}
                      </span>
                      <span className="mt-0.5 block truncate text-[13px] text-slate-600 dark:text-slate-300">{t.titulo || '—'}</span>
                    </span>
                    <span className="hidden shrink-0 text-xs text-slate-500 sm:block dark:text-slate-400">{t.modulo}</span>
                    <ChevronRight className="h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  )
}
