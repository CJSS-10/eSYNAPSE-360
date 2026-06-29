import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '../lib/api.js'

const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
const COLOR = {
  verde: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
  azul: 'bg-esynapse-600/15 text-esynapse-600 dark:text-esynapse-300 border-esynapse-500/30',
  ambar: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30',
  rojo: 'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30',
}
const PUNTO = { verde: 'bg-emerald-500', azul: 'bg-esynapse-500', ambar: 'bg-amber-500', rojo: 'bg-red-500' }

export default function Calendario() {
  const navigate = useNavigate()
  const hoy = new Date()
  const [vista, setVista] = useState('mes') // dia | mes | anio
  const [cursor, setCursor] = useState(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()))
  const [eventos, setEventos] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [usuario, setUsuario] = useState('')

  const cargar = useCallback(() => {
    api.calendario(usuario || null).then((d) => setEventos(d.eventos || [])).catch(() => {})
  }, [usuario])
  useEffect(() => { cargar() }, [cargar])
  useEffect(() => { api.usuarios.listar().then((d) => setUsuarios(d.results ?? d)).catch(() => {}) }, [])

  const porFecha = useMemo(() => {
    const m = {}
    eventos.forEach((e) => { (m[e.fecha] = m[e.fecha] || []).push(e) })
    return m
  }, [eventos])

  const iso = (y, mo, d) => `${y}-${String(mo + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`

  const navegar = (dir) => {
    const c = new Date(cursor)
    if (vista === 'mes') c.setMonth(c.getMonth() + dir)
    else if (vista === 'anio') c.setFullYear(c.getFullYear() + dir)
    else c.setDate(c.getDate() + dir)
    setCursor(c)
  }

  const titulo = vista === 'anio' ? cursor.getFullYear()
    : vista === 'mes' ? `${MESES[cursor.getMonth()]} ${cursor.getFullYear()}`
    : `${cursor.getDate()} de ${MESES[cursor.getMonth()]} ${cursor.getFullYear()}`

  // Construye la grilla del mes (lunes a domingo)
  const gridMes = (anio, mes) => {
    const primero = new Date(anio, mes, 1)
    let inicio = primero.getDay() - 1; if (inicio < 0) inicio = 6 // lunes=0
    const dias = new Date(anio, mes + 1, 0).getDate()
    const celdas = []
    for (let i = 0; i < inicio; i++) celdas.push(null)
    for (let d = 1; d <= dias; d++) celdas.push(d)
    return celdas
  }

  const evento = (e, i) => (
    <button key={i} onClick={() => navigate(e.ruta)}
      className={`mb-0.5 block w-full truncate rounded border px-1 py-0.5 text-left text-[10px] ${COLOR[e.color] || 'bg-slate-200'}`}
      title={`${e.titulo}${e.persona ? ' · ' + e.persona : ''}`}>
      {e.titulo}
    </button>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <CalendarDays className="h-6 w-6 text-esynapse-500" />
          <h1 className="text-2xl font-bold">Calendario</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select className="input-esynapse w-48" value={usuario} onChange={(e) => setUsuario(e.target.value)}>
            <option value="">Todas las personas</option>
            {usuarios.map((u) => <option key={u.id} value={u.id}>{u.nombre_completo}</option>)}
          </select>
          <div className="flex rounded-lg border border-slate-300 p-0.5 text-xs dark:border-slate-700">
            {['dia', 'mes', 'anio'].map((v) => (
              <button key={v} onClick={() => setVista(v)}
                className={`rounded px-2.5 py-1 capitalize ${vista === v ? 'bg-esynapse-600 text-white' : 'text-slate-500'}`}>
                {v === 'dia' ? 'Día' : v === 'mes' ? 'Mes' : 'Año'}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <button onClick={() => navegar(-1)} className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"><ChevronLeft className="h-4 w-4" /></button>
          <button onClick={() => navegar(1)} className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"><ChevronRight className="h-4 w-4" /></button>
          <button onClick={() => setCursor(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()))} className="ml-1 rounded-lg border border-slate-300 px-2 py-1 text-xs text-slate-500 dark:border-slate-700">Hoy</button>
        </div>
        <h2 className="text-lg font-semibold capitalize">{titulo}</h2>
        <div className="flex items-center gap-3 text-[10px] text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" /> Acciones</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-esynapse-500" /> Auditorías</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-500" /> Revisión doc.</span>
        </div>
      </div>

      {/* Vista MES */}
      {vista === 'mes' && (
        <div className="card-esynapse overflow-hidden">
          <div className="grid grid-cols-7 border-b border-slate-200 text-center text-[11px] font-semibold text-slate-500 dark:border-slate-800 dark:text-slate-400">
            {DIAS.map((d) => <div key={d} className="py-2">{d}</div>)}
          </div>
          <div className="grid grid-cols-7">
            {gridMes(cursor.getFullYear(), cursor.getMonth()).map((d, i) => {
              const fecha = d ? iso(cursor.getFullYear(), cursor.getMonth(), d) : null
              const evs = fecha ? (porFecha[fecha] || []) : []
              const esHoy = fecha === iso(hoy.getFullYear(), hoy.getMonth(), hoy.getDate())
              return (
                <div key={i} className={`min-h-[90px] border-b border-r border-slate-100 p-1 dark:border-slate-800/60 ${!d ? 'bg-slate-50/50 dark:bg-slate-900/40' : ''}`}>
                  {d && (
                    <>
                      <p className={`mb-0.5 text-right text-[11px] ${esHoy ? 'font-bold text-esynapse-600 dark:text-esynapse-300' : 'text-slate-400'}`}>{d}</p>
                      {evs.slice(0, 3).map(evento)}
                      {evs.length > 3 && <p className="text-[9px] text-slate-400">+{evs.length - 3} más</p>}
                    </>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Vista DÍA */}
      {vista === 'dia' && (
        <div className="card-esynapse p-4">
          {(porFecha[iso(cursor.getFullYear(), cursor.getMonth(), cursor.getDate())] || []).length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-400">Sin pendientes este día.</p>
          ) : (
            <ul className="space-y-2">
              {(porFecha[iso(cursor.getFullYear(), cursor.getMonth(), cursor.getDate())] || []).map((e, i) => (
                <li key={i}>
                  <button onClick={() => navigate(e.ruta)} className={`flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left text-sm ${COLOR[e.color]}`}>
                    <span>{e.titulo}</span>
                    {e.persona && <span className="text-xs opacity-70">{e.persona}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Vista AÑO */}
      {vista === 'anio' && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          {MESES.map((nombre, mes) => {
            const delMes = eventos.filter((e) => {
              const [y, m] = e.fecha.split('-').map(Number)
              return y === cursor.getFullYear() && m === mes + 1
            })
            return (
              <button key={mes} onClick={() => { setCursor(new Date(cursor.getFullYear(), mes, 1)); setVista('mes') }}
                className="card-esynapse p-3 text-left transition hover:ring-2 hover:ring-esynapse-500/30">
                <p className="text-sm font-semibold">{nombre}</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{delMes.length} pendiente{delMes.length === 1 ? '' : 's'}</p>
                <div className="mt-1 flex flex-wrap gap-0.5">
                  {delMes.slice(0, 12).map((e, i) => <span key={i} className={`h-1.5 w-1.5 rounded-full ${PUNTO[e.color] || 'bg-slate-400'}`} />)}
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
