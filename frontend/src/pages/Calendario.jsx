import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '../lib/api.js'
import TituloModulo from '../components/ui/TituloModulo.jsx'

const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
// Cada módulo tiene su color de barra (identifica de dónde viene el pendiente). El estado no se
// expresa con el color del módulo: lo vencido se marca aparte, en rojo, para no confundirlo con
// el verde de «cerrado» o el ámbar de «por vencer».
const MODULO = {
  accion: ['Acciones correctivas', 'border-l-esynapse-600', 'bg-esynapse-600'],
  auditoria: ['Auditorías', 'border-l-violet-500', 'bg-violet-500'],
  calibracion: ['Calibración de equipos', 'border-l-teal-600', 'bg-teal-600'],
  revision_doc: ['Revisión de documentos', 'border-l-amber-500', 'bg-amber-500'],
  seguimiento: ['Seguimiento de competencia', 'border-l-slate-500', 'bg-slate-500'],
}
const BARRA = (e) => MODULO[e.tipo]?.[1] || 'border-l-slate-400'
const PUNTO = (e) => MODULO[e.tipo]?.[2] || 'bg-slate-400'

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
    // Mes y año se mueven desde el día 1: el 31 de octubre + 1 mes no debe saltar a diciembre.
    if (vista === 'mes') { c.setDate(1); c.setMonth(c.getMonth() + dir) }
    else if (vista === 'anio') { c.setDate(1); c.setFullYear(c.getFullYear() + dir) }
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

  const hoyIso = iso(hoy.getFullYear(), hoy.getMonth(), hoy.getDate())
  const vencido = (e) => e.fecha < hoyIso || e.color === 'rojo'
  const evento = (e, i) => (
    <button key={i} onClick={() => navigate(e.ruta)}
      className={`mb-1 block w-full truncate rounded-r border-l-[3px] bg-slate-50 px-1.5 py-0.5 text-left text-xs hover:bg-slate-100 dark:bg-slate-800/70 dark:hover:bg-slate-800 ${BARRA(e)} ${vencido(e) ? 'font-medium text-red-700 dark:text-red-300' : 'text-slate-700 dark:text-slate-200'}`}
      title={`${MODULO[e.tipo]?.[0] || e.modulo} · ${e.titulo}${e.persona ? ' · ' + e.persona : ''}${vencido(e) ? ' · vencido' : ''}`}>
      {e.titulo}
    </button>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <TituloModulo seccion="General" titulo="Calendario"
          descripcion="Los plazos de todos los módulos por fecha. Lo vencido aparece en rojo; filtre por persona para ver lo de cada uno." />
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
          <button onClick={() => navegar(-1)} aria-label="Anterior" className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"><ChevronLeft className="h-4 w-4" /></button>
          <button onClick={() => navegar(1)} aria-label="Siguiente" className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"><ChevronRight className="h-4 w-4" /></button>
          <button onClick={() => setCursor(new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()))} className="ml-1 rounded-lg border border-slate-300 px-2.5 py-1 text-[13px] font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">Hoy</button>
        </div>
        <h2 className="text-lg font-semibold capitalize">{titulo}</h2>
        <div className="flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
          {Object.entries(MODULO).map(([k, [nombre, , punto]]) => (
            <span key={k} className="flex items-center gap-1.5"><span className={`h-3 w-[3px] rounded-full ${punto}`} />{nombre}</span>
          ))}
          <span className="flex items-center gap-1.5 font-medium text-red-700 dark:text-red-300">Vencido</span>
        </div>
      </div>

      {/* Vista MES */}
      {vista === 'mes' && (
        <div className="card-esynapse overflow-hidden">
          <div className="grid grid-cols-7 border-b border-slate-200 text-[13px] font-semibold text-slate-500 dark:border-slate-800 dark:text-slate-400">
            {DIAS.map((d, i) => <div key={d} className={`px-2 py-2 ${i > 4 ? 'bg-slate-50 dark:bg-slate-900/50' : ''}`}>{d}</div>)}
          </div>
          <div className="grid grid-cols-7">
            {gridMes(cursor.getFullYear(), cursor.getMonth()).map((d, i) => {
              const fecha = d ? iso(cursor.getFullYear(), cursor.getMonth(), d) : null
              const evs = fecha ? (porFecha[fecha] || []) : []
              const esHoy = fecha === hoyIso
              const finDeSemana = i % 7 > 4
              return (
                <div key={i} className={`min-h-[96px] border-b border-r border-slate-100 p-1.5 dark:border-slate-800/60 ${!d ? 'bg-slate-100/60 dark:bg-slate-950/40' : finDeSemana ? 'bg-slate-50 dark:bg-slate-900/50' : ''}`}>
                  {d && (
                    <>
                      <p className="mb-1">
                        <span className={`inline-flex h-6 min-w-6 items-center justify-center rounded-full px-1 text-xs font-semibold ${esHoy ? 'bg-esynapse-600 text-white' : fecha < hoyIso ? 'text-slate-400 dark:text-slate-500' : 'text-slate-700 dark:text-slate-200'}`}
                          aria-current={esHoy ? 'date' : undefined}>{d}</span>
                      </p>
                      {evs.slice(0, 3).map(evento)}
                      {evs.length > 3 && (
                        <button onClick={() => { setCursor(new Date(cursor.getFullYear(), cursor.getMonth(), d)); setVista('dia') }}
                          className="text-xs font-semibold text-esynapse-600 hover:underline dark:text-esynapse-300">y {evs.length - 3} más</button>
                      )}
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
            <p className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">Sin pendientes este día.</p>
          ) : (
            <ul className="space-y-2">
              {(porFecha[iso(cursor.getFullYear(), cursor.getMonth(), cursor.getDate())] || []).map((e, i) => (
                <li key={i}>
                  <button onClick={() => navigate(e.ruta)} className={`flex w-full items-center justify-between gap-3 rounded-r-lg border-l-4 bg-slate-50 px-3 py-2.5 text-left text-sm hover:bg-slate-100 dark:bg-slate-800/70 dark:hover:bg-slate-800 ${BARRA(e)}`}>
                    <span className="min-w-0">
                      <span className="block text-xs text-slate-500 dark:text-slate-400">{MODULO[e.tipo]?.[0] || e.modulo}{vencido(e) && <span className="ml-2 font-semibold text-red-700 dark:text-red-300">Vencido</span>}</span>
                      <span className={vencido(e) ? 'font-medium text-red-700 dark:text-red-300' : ''}>{e.titulo}</span>
                    </span>
                    {e.persona && <span className="shrink-0 text-xs text-slate-500 dark:text-slate-400">{e.persona}</span>}
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
                  {delMes.slice(0, 12).map((e, i) => <span key={i} className={`h-1.5 w-1.5 rounded-full ${PUNTO(e)}`} />)}
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
