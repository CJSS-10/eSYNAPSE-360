import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api.js'
import { useAuth } from '../context/AuthContext.jsx'
import { SkeletonText } from '../components/ui/Skeleton.jsx'
import { NormaBadge, EstadoBadge } from '../components/ui/Badge.jsx'
import { SEVERIDAD } from '../lib/severidad.js'

// Tablero del SIG (ADR-0007): vencimientos de todos los módulos en una vista, el estado de cada
// módulo y las tareas de la persona. Todo sale de los datos del sistema; un módulo sin permiso
// o sin respuesta simplemente no aparece.

const COLUMNAS = [
  ['vencido', 'Vencido'], ['d7', 'Próximos 7 días'], ['d30', '8 a 30 días'], ['d60', '31 a 60 días'], ['d90', '61 a 90 días'],
]
// Filas de vencimientos: [clave, nombre visible, ruta]
const FILAS = [
  ['quejas', 'Quejas', '/quejas'],
  ['Acciones Correctivas', 'Acciones correctivas', '/acciones-correctivas'],
  ['riesgos', 'Riesgos y oportunidades', '/riesgos'],
  ['Equipos', 'Calibración de equipos', '/equipos'],
  ['Documentos', 'Revisión de documentos', '/documentos'],
  ['Competencia Técnica', 'Seguimiento de competencia', '/competencia'],
  ['Auditorías', 'Auditorías programadas', '/auditorias'],
]
const PASOS_SAC = [
  ['registrada', 'Registro', 'bg-slate-500/15 text-slate-700 dark:text-slate-200'],
  ['en_analisis', 'Análisis', 'bg-amber-500/15 text-amber-700 dark:text-amber-300'],
  ['en_implementacion', 'Implem.', 'bg-esynapse-600/15 text-esynapse-700 dark:text-esynapse-300'],
  ['en_verificacion', 'Verif.', 'bg-violet-500/15 text-violet-700 dark:text-violet-300'],
  ['cerrada', 'Cerradas', 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'],
]
const NIVELES_IPERC = [['T', 'Trivial', 1], ['TO', 'Tolerable', 2], ['M', 'Moderado', 3], ['IM', 'Importante', 4], ['IT', 'Intolerable', 5]]

const hoyISO = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d }
const columnaDe = (fecha) => {
  if (!fecha) return null
  const dias = Math.round((new Date(`${fecha.slice(0, 10)}T00:00:00`) - hoyISO()) / 86400000)
  if (dias < 0) return 'vencido'
  if (dias <= 7) return 'd7'
  if (dias <= 30) return 'd30'
  if (dias <= 60) return 'd60'
  if (dias <= 90) return 'd90'
  return null
}
const fechaCorta = (f) => new Date(`${f.slice(0, 10)}T00:00:00`).toLocaleDateString('es-PE', { day: 'numeric', month: 'short' })
const saludo = () => { const h = new Date().getHours(); return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches' }
const lista = (r) => (r?.results ?? r ?? [])

export default function Dashboard() {
  const { usuario } = useAuth()
  const [cargando, setCargando] = useState(true)
  const [d, setD] = useState({ celdas: {}, filas: [], tareas: [], modulos: {} })

  useEffect(() => {
    let vivo = true
    Promise.allSettled([
      api.calendario(), api.quejas.listar('?abiertas=1'), api.riesgos.listar(), api.misTareas(),
      api.sac.listar(), api.hallazgos.resumen(), api.equipos.resumen(), api.documentos.porVencer(), api.sst.resumen(),
    ]).then(([cal, que, rie, tar, sac, hal, equ, doc, ipe]) => {
      if (!vivo) return
      const ok = (r) => r.status === 'fulfilled'
      const celdas = {}
      const poner = (fila, col, item) => {
        if (!col) return
        const k = `${fila}|${col}`
        ;(celdas[k] = celdas[k] || []).push(item)
      }
      const filasActivas = new Set()
      if (ok(cal)) {
        for (const e of cal.value.eventos || []) {
          filasActivas.add(e.modulo)
          poner(e.modulo, columnaDe(e.fecha), { texto: e.titulo, fecha: e.fecha, ruta: e.ruta })
        }
        // Las filas de módulos generales se muestran aunque no tengan fechas en el periodo
        ;['Acciones Correctivas', 'Equipos', 'Documentos', 'Competencia Técnica', 'Auditorías'].forEach((m) => filasActivas.add(m))
      }
      if (ok(que)) {
        filasActivas.add('quejas')
        for (const q of lista(que.value)) {
          if (q.alerta?.estado === 'vencido') poner('quejas', 'vencido', { texto: `${q.codigo}: ${q.alerta.nombre}`, ruta: '/quejas' })
        }
      }
      if (ok(rie)) {
        filasActivas.add('riesgos')
        for (const r of lista(rie.value)) {
          if (r.vencidas > 0) poner('riesgos', 'vencido', { texto: `${r.codigo}: ${r.vencidas} acción${r.vencidas > 1 ? 'es' : ''} del plan`, ruta: '/riesgos' })
        }
      }
      const modulos = {}
      if (ok(sac)) {
        const s = lista(sac.value)
        const cuenta = Object.fromEntries(PASOS_SAC.map(([k]) => [k, 0]))
        s.forEach((x) => { cuenta[x.estado.startsWith('cerrada') ? 'cerrada' : x.estado] = (cuenta[x.estado.startsWith('cerrada') ? 'cerrada' : x.estado] || 0) + 1 })
        modulos.sac = { total: s.length, abiertas: s.length - cuenta.cerrada, cuenta }
      }
      if (ok(hal)) modulos.hallazgos = hal.value
      if (ok(equ)) modulos.equipos = equ.value
      if (ok(doc)) modulos.documentos = Array.isArray(doc.value) ? doc.value.length : 0
      if (ok(que)) modulos.quejas = { abiertas: lista(que.value).length, vencidas: lista(que.value).filter((q) => q.alerta?.estado === 'vencido').length }
      if (ok(rie)) modulos.riesgos = { total: lista(rie.value).length, conVencidas: lista(rie.value).filter((r) => r.vencidas > 0).length }
      if (ok(ipe)) {
        const niveles = {}
        ;(ipe.value.areas || []).forEach((a) => Object.entries(a.niveles || {}).forEach(([k, v]) => { niveles[k] = (niveles[k] || 0) + v }))
        modulos.iperc = { total: ipe.value.total, niveles }
      }
      setD({
        celdas,
        filas: FILAS.filter(([k]) => filasActivas.has(k)),
        tareas: ok(tar) ? (tar.value.tareas || []) : [],
        modulos,
      })
      setCargando(false)
    })
    return () => { vivo = false }
  }, [])

  const n = (col) => d.filas.reduce((s, [k]) => s + (d.celdas[`${k}|${col}`]?.length || 0), 0)
  const tienePlazos = ([k]) => COLUMNAS.some(([c]) => d.celdas[`${k}|${c}`]?.length)
  const conPlazos = d.filas.filter(tienePlazos)
  const sinPlazos = d.filas.filter((f) => !tienePlazos(f))
  const vencidos = n('vencido')
  const semana = n('d7')
  const m = d.modulos
  const nombre = usuario?.first_name || usuario?.nombre_completo?.split(' ')[0] || usuario?.username || ''

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[26px] font-semibold leading-tight tracking-tight">{saludo()}, {nombre}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {new Date().toLocaleDateString('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).replace(/^./, (c) => c.toUpperCase())}
          </p>
        </div>
        {!cargando && (
          <div className="flex flex-wrap gap-2 text-[13px] font-semibold">
            {vencidos > 0 && <span className="rounded-full bg-red-500/10 px-3 py-1 text-red-700 dark:text-red-300">{vencidos} vencido{vencidos > 1 ? 's' : ''}</span>}
            {semana > 0 && <span className="rounded-full bg-amber-500/15 px-3 py-1 text-amber-700 dark:text-amber-300">{semana} vence{semana > 1 ? 'n' : ''} esta semana</span>}
            <Link to="/mis-tareas" className="rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800">
              {d.tareas.length} tarea{d.tareas.length === 1 ? '' : 's'} asignada{d.tareas.length === 1 ? '' : 's'} a ti
            </Link>
          </div>
        )}
      </header>

      {/* Vencimientos */}
      <section className="card-esynapse" aria-labelledby="t-venc">
        <div className="flex flex-wrap items-baseline justify-between gap-3 px-5 pb-3 pt-4">
          <div>
            <h2 id="t-venc" className="text-[17px] font-semibold">Vencimientos</h2>
            <p className="text-[13px] text-slate-500 dark:text-slate-400">Plazos de todos los módulos en una sola vista. La primera columna es lo que ya venció.</p>
          </div>
          <Link to="/calendario" className="text-[13px] font-semibold text-esynapse-600 hover:underline dark:text-esynapse-300">Abrir calendario</Link>
        </div>
        {cargando ? <div className="px-5 pb-5"><SkeletonText lines={5} /></div> : (
          <div className="overflow-x-auto border-t border-slate-200 dark:border-slate-800">
            <div className="grid min-w-[900px] grid-cols-[minmax(170px,1.3fr)_repeat(5,minmax(130px,1fr))] text-[13px]">
              <div className="border-b border-slate-200 bg-slate-50 px-4 py-2.5 font-condensada font-semibold text-slate-500 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-400">Módulo</div>
              {COLUMNAS.map(([k, t]) => (
                <div key={k} className={`border-b border-l border-slate-200 px-3 py-2.5 font-condensada font-semibold dark:border-slate-800 ${k === 'vencido' ? 'bg-red-500/[0.06] text-red-700 dark:text-red-300' : 'bg-slate-50 text-slate-500 dark:bg-slate-900/60 dark:text-slate-400'}`}>{t}</div>
              ))}
              {conPlazos.map(([k, nombreFila, ruta]) => (
                <Fila key={k} clave={k} nombre={nombreFila} ruta={ruta} celdas={d.celdas} />
              ))}
            </div>
            {conPlazos.length === 0 && (
              <p className="px-5 py-4 text-[13px] text-slate-500 dark:text-slate-400">Nada vence en los próximos 90 días.</p>
            )}
            {sinPlazos.length > 0 && (
              <p className="border-t border-slate-200 px-5 py-2.5 text-[13px] text-slate-500 dark:border-slate-800 dark:text-slate-400">
                Sin vencimientos en los próximos 90 días:{' '}
                {sinPlazos.map(([k, nombreFila, ruta], i) => (
                  <span key={k}>{i > 0 && ', '}<Link to={ruta} className="font-medium text-slate-700 hover:underline dark:text-slate-200">{nombreFila}</Link></span>
                ))}.
              </p>
            )}
          </div>
        )}
      </section>

      <div className="flex flex-wrap items-start gap-6">
        {/* Estado por módulo */}
        <section aria-label="Estado por módulo" className="grid min-w-0 flex-[999_1_560px] grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-4">
          {cargando && [1, 2, 3].map((i) => <div key={i} className="card-esynapse p-4"><SkeletonText lines={3} /></div>)}
          {m.sac && (
            <Tarjeta titulo="Acciones correctivas" norma="ISO 9001" ruta="/acciones-correctivas" numero={m.sac.abiertas} unidad={`abiertas de ${m.sac.total}`}>
              <div className="flex gap-1" aria-label="Solicitudes por etapa">
                {PASOS_SAC.map(([k, t, cls]) => (
                  <div key={k} className="flex-1 text-center">
                    <div className={`rounded py-1 text-xs font-semibold ${m.sac.cuenta[k] ? cls : 'border border-dashed border-slate-200 text-slate-400 dark:border-slate-700'}`}>{m.sac.cuenta[k] || 0}</div>
                    <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{t}</div>
                  </div>
                ))}
              </div>
            </Tarjeta>
          )}
          {m.hallazgos && (
            <Tarjeta titulo="Hallazgos" norma="NTP ISO/IEC 17025" ruta="/hallazgos" numero={m.hallazgos.abiertos} unidad="abiertos">
              <p className="text-[13px] text-slate-500 dark:text-slate-400">
                {m.hallazgos.por_estado?.registrado || 0} registrados, {m.hallazgos.por_estado?.en_tratamiento || 0} en tratamiento y {m.hallazgos.por_estado?.derivado || 0} derivados a riesgos y oportunidades.
              </p>
            </Tarjeta>
          )}
          {m.quejas && (
            <Tarjeta titulo="Quejas" norma="NTP ISO/IEC 17025" ruta="/quejas" numero={m.quejas.abiertas} unidad="abiertas" alerta={m.quejas.vencidas > 0}>
              <p className="text-[13px] text-slate-500 dark:text-slate-400">
                {m.quejas.vencidas > 0 ? `${m.quejas.vencidas} con un plazo vencido.` : 'Todas dentro de plazo.'}
              </p>
            </Tarjeta>
          )}
          {m.iperc && (
            <Tarjeta titulo="Matriz IPERC" norma="ISO 45001 / Ley 29783" ruta="/sst" numero={m.iperc.total} unidad="filas vigentes">
              <div className="flex flex-wrap gap-1.5">
                {NIVELES_IPERC.filter(([k]) => m.iperc.niveles[k]).map(([k, t, nivel]) => (
                  <span key={k} className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold ${SEVERIDAD[nivel].chip}`}>{t} {m.iperc.niveles[k]}</span>
                ))}
              </div>
            </Tarjeta>
          )}
          {m.equipos && (
            <Tarjeta titulo="Equipos" norma="NTP ISO/IEC 17025" ruta="/equipos"
              numero={Object.values(m.equipos.por_estado || {}).reduce((a, b) => a + b, 0)} unidad="registrados" alerta={m.equipos.vencidos > 0}>
              <p className="text-[13px] text-slate-500 dark:text-slate-400">
                {m.equipos.vencidos > 0 ? `${m.equipos.vencidos} con la calibración vencida. ` : ''}
                {m.equipos.por_vencer_30 ? `${m.equipos.por_vencer_30} por calibrar en 30 días.` : 'Ninguna calibración vence en los próximos 30 días.'}
              </p>
            </Tarjeta>
          )}
          {m.riesgos && (
            <Tarjeta titulo="Riesgos y oportunidades" norma="ISO 9001" ruta="/riesgos" numero={m.riesgos.conVencidas} unidad="con acciones vencidas" alerta={m.riesgos.conVencidas > 0}>
              <p className="text-[13px] text-slate-500 dark:text-slate-400">De {m.riesgos.total} registros en la matriz.</p>
            </Tarjeta>
          )}
          {m.documentos !== undefined && (
            <Tarjeta titulo="Documentos" ruta="/documentos" numero={m.documentos} unidad="por revisar" alerta={m.documentos > 0}>
              <p className="text-[13px] text-slate-500 dark:text-slate-400">Con la revisión próxima o vencida.</p>
            </Tarjeta>
          )}
        </section>

        {/* Mis pendientes */}
        <section className="card-esynapse min-w-0 flex-[1_1_300px] lg:max-w-sm" aria-labelledby="t-pend">
          <div className="px-5 pb-2 pt-4">
            <h2 id="t-pend" className="text-[17px] font-semibold">Tus pendientes</h2>
            <p className="text-[13px] text-slate-500 dark:text-slate-400">Lo que espera una acción tuya</p>
          </div>
          {cargando ? <div className="px-5 pb-5"><SkeletonText lines={4} /></div> : d.tareas.length === 0 ? (
            <p className="px-5 pb-6 pt-2 text-sm text-slate-500 dark:text-slate-400">No tienes tareas pendientes.</p>
          ) : (
            <ul className="px-2 pb-2">
              {d.tareas.slice(0, 6).map((t, i) => (
                <li key={i}>
                  <Link to={t.ruta || '/mis-tareas'} className="flex flex-col gap-1 rounded-lg px-3 py-2.5 hover:bg-slate-50 dark:hover:bg-slate-800/60">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold">{t.codigo}</span>
                      <EstadoBadge estado={t.estado} />
                      {t.fecha && <span className="text-xs text-slate-500 dark:text-slate-400">vence {fechaCorta(t.fecha)}</span>}
                    </span>
                    <span className="line-clamp-1 text-[13px] text-slate-500 dark:text-slate-400">{t.titulo}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link to="/mis-tareas" className="block border-t border-slate-200 py-2.5 text-center text-[13px] font-semibold text-esynapse-600 hover:bg-slate-50 dark:border-slate-800 dark:text-esynapse-300 dark:hover:bg-slate-800/60">
            Ver todas mis tareas
          </Link>
        </section>
      </div>
    </div>
  )
}

function Fila({ clave, nombre, ruta, celdas }) {
  return (
    <>
      <div className="flex items-center border-b border-slate-100 px-4 py-2.5 font-semibold dark:border-slate-800/60">
        <Link to={ruta} className="hover:underline">{nombre}</Link>
      </div>
      {COLUMNAS.map(([col]) => {
        const items = celdas[`${clave}|${col}`] || []
        return (
          <div key={col} className={`flex flex-wrap content-center items-center gap-1.5 border-b border-l border-slate-100 px-3 py-2 dark:border-slate-800/60 ${col === 'vencido' && items.length ? 'bg-red-500/[0.06]' : ''}`}>
            {items.length === 0 && <span className="text-slate-300 dark:text-slate-600" aria-label="Ninguno">—</span>}
            {items.slice(0, 3).map((it, i) => {
              const codigo = it.texto.includes(':') ? it.texto.split(':')[0] : it.texto
              return (
                <Link key={i} to={it.ruta || ruta} title={`${it.texto}${it.fecha ? ` · ${fechaCorta(it.fecha)}` : ''}`}
                  className={`inline-flex max-w-full items-baseline gap-1.5 truncate rounded-md border px-2 py-0.5 text-xs hover:underline ${col === 'vencido' ? 'border-red-300 bg-white text-red-800 dark:border-red-500/40 dark:bg-slate-900 dark:text-red-300' : 'border-slate-200 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200'}`}>
                  <span className="font-mono font-medium">{codigo.length > 18 ? `${codigo.slice(0, 17)}…` : codigo}</span>
                  {it.fecha && <span className="text-slate-500 dark:text-slate-400">{fechaCorta(it.fecha)}</span>}
                </Link>
              )
            })}
            {items.length > 3 && <Link to={ruta} className="text-xs font-semibold text-esynapse-600 hover:underline dark:text-esynapse-300">y {items.length - 3} más</Link>}
          </div>
        )
      })}
    </>
  )
}

function Tarjeta({ titulo, norma, ruta, numero, unidad, alerta = false, children }) {
  return (
    <Link to={ruta} className="card-esynapse card-hover flex flex-col gap-3 p-4">
      <span className="flex items-start justify-between gap-2">
        <span className="text-[15px] font-semibold">{titulo}</span>
        {norma && <NormaBadge nombre={norma} />}
      </span>
      <span className="flex items-baseline gap-2">
        <span className={`text-3xl font-semibold leading-none ${alerta ? 'text-red-700 dark:text-red-300' : ''}`}>{numero ?? '—'}</span>
        <span className="text-[13px] text-slate-500 dark:text-slate-400">{unidad}</span>
      </span>
      {children}
    </Link>
  )
}
