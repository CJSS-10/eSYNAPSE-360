import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Boxes, CalendarClock, FileWarning, AlertOctagon, ArrowRight, LayoutDashboard, Inbox,
} from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import KpiCard from '../components/ui/KpiCard.jsx'
import { SkeletonText } from '../components/ui/Skeleton.jsx'

const ESTADO_EQUIPO = {
  operativo: { label: 'Operativo', color: '#1d60f1' },
  calibrado: { label: 'Calibrado', color: '#10b981' },
  inoperativo: { label: 'Inoperativo', color: '#f59e0b' },
  baja: { label: 'De baja', color: '#ef4444' },
}

const ICONO_TAREA = { Hallazgos: AlertOctagon, Documentos: FileWarning, Equipos: Boxes }

export default function Dashboard() {
  const { usuario } = useAuth()
  const [cargando, setCargando] = useState(true)
  const [d, setD] = useState({
    equiposPorEstado: {}, equiposTotal: 0, equiposPorVencer: 0,
    docsPorRevisar: 0, hallazgosAbiertos: 0, tareas: [],
  })

  useEffect(() => {
    let vivo = true
    const num = (r) => (r?.count ?? (Array.isArray(r) ? r.length : (Array.isArray(r?.results) ? r.results.length : 0)))
    Promise.allSettled([
      api.equipos.resumen(),
      api.documentos.porVencer(),
      api.hallazgos.listar(),
      api.misTareas(),
    ]).then(([eq, dv, ha, mt]) => {
      if (!vivo) return
      const por = eq.status === 'fulfilled' ? (eq.value.por_estado || {}) : {}
      const total = Object.values(por).reduce((a, b) => a + b, 0)
      setD({
        equiposPorEstado: por,
        equiposTotal: total,
        equiposPorVencer: eq.status === 'fulfilled' ? (eq.value.por_vencer_30 ?? 0) : 0,
        docsPorRevisar: dv.status === 'fulfilled' ? (Array.isArray(dv.value) ? dv.value.length : 0) : 0,
        hallazgosAbiertos: ha.status === 'fulfilled' ? num(ha.value) : 0,
        tareas: mt.status === 'fulfilled' ? (mt.value.tareas || []) : [],
      })
      setCargando(false)
    })
    return () => { vivo = false }
  }, [])

  const chart = Object.entries(d.equiposPorEstado)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: ESTADO_EQUIPO[k]?.label || k, value: v, color: ESTADO_EQUIPO[k]?.color || '#94a3b8' }))

  const kpis = [
    { label: 'Equipos registrados', value: d.equiposTotal, icon: Boxes, tono: 'azul', hint: 'Inventario total' },
    { label: 'Por calibrar (30 días)', value: d.equiposPorVencer, icon: CalendarClock, tono: d.equiposPorVencer ? 'ambar' : 'verde', hint: 'Próximos vencimientos' },
    { label: 'Documentos por revisar', value: d.docsPorRevisar, icon: FileWarning, tono: d.docsPorRevisar ? 'ambar' : 'verde', hint: 'Revisión próxima o vencida' },
    { label: 'Hallazgos abiertos', value: d.hallazgosAbiertos, icon: AlertOctagon, tono: d.hallazgosAbiertos ? 'rojo' : 'verde', hint: 'En registro o tratamiento' },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        icon={LayoutDashboard}
        title={`Hola, ${usuario?.first_name || usuario?.username || ''}`.trim()}
        subtitle={`${usuario?.cargo ? usuario.cargo + ' · ' : ''}${usuario?.area || 'eSYNAPSE 360°'}`}
      />

      {/* KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((k) => (
          <KpiCard key={k.label} {...k} value={cargando ? '—' : k.value} />
        ))}
      </div>

      {/* Gráfico + pendientes */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Equipos por estado */}
        <div className="card-esynapse lg:col-span-2">
          <div className="card-head">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-esynapse-600/12 text-esynapse-600 dark:text-esynapse-300">
              <Boxes className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-semibold">Equipos por estado</h2>
              <p className="text-xs muted">Distribución del inventario de equipos</p>
            </div>
          </div>
          <div className="card-pad">
            {cargando ? (
              <SkeletonText lines={4} />
            ) : chart.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <Boxes className="h-10 w-10 text-slate-300 dark:text-slate-700" />
                <p className="mt-2 text-sm muted">Aún no hay equipos registrados.</p>
                <Link to="/equipos" className="btn-primary mt-3 !py-1.5 text-xs">Registrar equipo</Link>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 sm:flex-row">
                <div className="h-48 w-48 shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={chart} dataKey="value" nameKey="name" innerRadius={52} outerRadius={80} paddingAngle={2} stroke="none">
                        {chart.map((e) => <Cell key={e.name} fill={e.color} />)}
                      </Pie>
                      <Tooltip
                        contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 10px 30px -10px rgba(15,23,42,.25)', fontSize: 12 }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="flex-1 space-y-2">
                  {chart.map((e) => (
                    <li key={e.name} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: e.color }} />
                        {e.name}
                      </span>
                      <span className="font-semibold">{e.value}</span>
                    </li>
                  ))}
                  <li className="flex items-center justify-between border-t border-slate-100 pt-2 text-sm dark:border-slate-800">
                    <span className="muted">Total</span>
                    <span className="font-bold">{d.equiposTotal}</span>
                  </li>
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Pendientes */}
        <div className="card-esynapse">
          <div className="card-head">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/15 text-amber-600 dark:text-amber-300">
              <Inbox className="h-5 w-5" />
            </span>
            <div>
              <h2 className="font-semibold">Mis pendientes</h2>
              <p className="text-xs muted">Tareas que requieren tu atención</p>
            </div>
          </div>
          <div className="card-pad">
            {cargando ? (
              <SkeletonText lines={4} />
            ) : d.tareas.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-sm muted">Estás al día. Sin pendientes.</p>
              </div>
            ) : (
              <ul className="space-y-1">
                {d.tareas.slice(0, 5).map((t, i) => {
                  const Ico = ICONO_TAREA[t.modulo] || Inbox
                  return (
                    <li key={i}>
                      <Link to={t.ruta || '/mis-tareas'} className="flex items-start gap-2 rounded-lg px-2 py-2 transition hover:bg-slate-100 dark:hover:bg-slate-800">
                        <Ico className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{t.codigo} <span className="font-normal muted">· {t.estado}</span></span>
                          <span className="block truncate text-xs muted">{t.titulo}</span>
                        </span>
                      </Link>
                    </li>
                  )
                })}
                <li>
                  <Link to="/mis-tareas" className="mt-1 flex items-center justify-center gap-1 rounded-lg py-2 text-xs font-medium text-esynapse-600 hover:bg-slate-100 dark:text-esynapse-300 dark:hover:bg-slate-800">
                    Ver todas <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </li>
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
